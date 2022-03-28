from dataclasses import dataclass
from pool import *


@dataclass
class Vertex:
    amount_out: Dec
    spread: Dec
    route: Union[tuple, list]

    def __eq__(self, other):
        return True if self.spread == other.spread else False

    def __gt__(self, other):
        return True if self.spread > other.spread else False

    def __lt__(self, other):
        return True if self.spread < other.spread else False


@dataclass
class Route:
    route: Union[tuple, list]
    trade: Trade
    swaps: list[Trade]

    def __repr__(self):
        return f"Route: {self.route}\n{self.trade}"


class Dex:
    def __init__(self, dex: str):
        self.dex = dex
        if dex in router:
            self.router = AccAddress(router[dex])
        else:
            self.router = AccAddress('')

    def adjacent(self, token_in: str):
        """Tokens forming a trading pair with token_in
        :return: adjacency list
        """
        return [pool.other(token_in) for pool, info in pools_info.items()
                if token_in in pool.pair and self.dex in info]

    def dfs(self, token_in: str, token_out: str):
        """Depth first search for possible trading routes
        """
        token_in, token_out = token_in.lower(), token_out.lower()
        pairs = {token_in: self.adjacent(token_in)}
        route = (token_in,)
        stack = [route]
        res = []
        while stack:
            route = stack.pop()
            node = route[-1]
            if node == token_out:
                res.append(route)
            else:
                if node not in pairs:
                    pairs[node] = self.adjacent(node)
                for token in pairs[node]:
                    if token not in route:
                        stack.append(route + (token,))
        return res

    def assertion(self, token_in: str, token_out: str):
        token_in, token_out = token_in.lower(), token_out.lower()
        assert token_in in tokens_info, f"No token info {token_in}"
        assert self.dex in get_dex(token_in), f"{token_in} not trading on {self.dex}"
        assert token_out in tokens_info, f"No token info {token_out}"
        assert self.dex in get_dex(token_out), f"{token_out} not trading on {self.dex}"
        return token_in, token_out

    async def dijkstra_routing(self, token_in: str, amount_in: Union[int, float, Dec], token_out: str):
        """Find the route with the least spread using Dijkstra's algorithm

        :return: Route(route, trade, swaps)
        """
        token_in, token_out = self.assertion(token_in, token_out)

        if not isinstance(amount_in, Dec):
            amount_in = to_Dec(amount_in, token_in)

        routes = self.dfs(token_in, token_out)
        if not routes:
            return None

        graph = set()
        for route in routes:
            graph.update(route)
        # Connected edges in the graph
        pools = dict()
        for route in routes:
            for i in range(len(route) - 1):
                pair = Pair(route[i], route[i + 1])
                if pair not in pools:
                    pools[pair] = Pool(pair, self.dex)
                if pair == Pair('luna', 'ust'):
                    pools['native_swap'] = Pool('luna', 'ust', 'native_swap')
        # Query liquidity in relevant pairs
        await asyncio.gather(*[pool.query() for pool in pools.values()])

        native = False
        min_vertex = Vertex(amount_in, Dec(0), (token_in,))
        heap = [min_vertex]
        spreads = {token: Dec(1) for token in graph}
        spreads[token_in] = Dec(0)
        visited = set()
        while heap:
            # Find the next token with the least spread
            min_vertex = heappop(heap)
            next_token = min_vertex.route[-1]
            visited.add(next_token)
            if next_token == token_out:
                break
            # Update spread of neighbors
            for neighbor in self.adjacent(next_token):
                if neighbor not in visited and neighbor in graph:
                    pair = Pair(next_token, neighbor)
                    trade = await pools[pair].simulate(next_token, min_vertex.amount_out)
                    if pair == Pair('luna', 'ust'):
                        native_swap = await pools['native_swap'].simulate(next_token, min_vertex.amount_out)
                        if native_swap.amount_out > trade.amount_out:
                            trade = native_swap
                            native = True
                    spread = spreads[next_token] + trade.spread - spreads[next_token] * trade.spread
                    if spread < spreads[neighbor]:
                        spreads[neighbor] = spread
                        heappush(heap, Vertex(trade.amount_out, spread, min_vertex.route + (neighbor,)))

        amount_out = expected = amount_in
        best_route: tuple[str] = min_vertex.route
        swaps: list[Trade] = []
        for i in range(len(best_route) - 1):
            pair = Pair(best_route[i], best_route[i + 1])
            if native and pair == Pair('luna', 'ust'):
                trade = await pools['native_swap'].simulate(best_route[i], amount_out)
            else:
                trade = await pools[pair].simulate(best_route[i], amount_out)
            amount_out = trade.amount_out
            swaps.append(trade)
            expected *= await pools[pair].price(best_route[i])
        spread = (expected - amount_out) / expected
        commission = expected * spread
        trade = Trade(self.dex, token_in, amount_in, token_out, amount_out, spread, commission)
        return Route(route=best_route, trade=trade, swaps=swaps)

    async def route_to_msg(self, routing: Route, minimum_receive=Dec(0)) -> Union[Msg, list[Msg]]:
        """Wrap trading route to a message
        """
        if routing is None:
            print('Impossible swap.')
            exit()
        trade, route, swaps = routing.trade, routing.route, routing.swaps
        token_in, amount_in = trade.token_in, trade.amount_in
        token_out, amount_out = trade.token_out, trade.amount_out

        if self.router:
            if minimum_receive == Dec(0):
                minimum_receive = amount_out * (1 - slippage)
            operations = []
            for i in range(len(swaps)):
                if swaps[i].dex == 'native_swap':
                    operation = {'native_swap': {
                        'offer_denom': get_denom(swaps[i].token_in),
                        'ask_denom': get_denom(swaps[i].token_out)
                    }}
                else:
                    operation = {swaps[i].dex: {
                        'offer_asset_info': asset_info(swaps[i].token_in),
                        'ask_asset_info': asset_info(swaps[i].token_out)
                    }}
                operations.append(operation)
            msg = {
                'execute_swap_operations': {
                    'offer_amount': amount_in.whole,
                    'minimum_receive': minimum_receive.whole,
                    'max_spread': f'{max_spread}',
                    'operations': operations
                }}
            # Message for native tokens
            if token_in in native_tokens:
                coins = Coins({get_denom(token_in): amount_in.whole})
                return MsgExecuteContract(wallet.key.acc_address, self.router, msg, coins)
            # Message for CW20 tokens
            else:
                execute_msg = {
                    'send': {
                        'contract': self.router,
                        'amount': amount_in.whole,
                        'msg': base64str_encode(msg)
                    }
                }
                return MsgExecuteContract(wallet.key.acc_address, get_contract(token_in), execute_msg)
        # Loop doesn't have a router.
        else:
            pools = [Pool(route[i], route[i + 1], self.dex) for i in range(len(swaps))]
            await asyncio.gather(*[pool.query() for pool in pools])

            msgs = []
            for i in range(len(swaps)):
                trade = await pools[i].simulate(route[i], amount_in)
                minimum_receive = trade.amount_out * (1 - slippage)
                msgs.append(await pools[i].trade_to_msg(trade, minimum_receive))
                # There may be leftovers.
                # Next input = last minimum_receive
                amount_in = minimum_receive
            return msgs

    async def swap_msg(self, token_in: str, amount_in: Union[int, float, Dec], token_out: str) -> Union[Msg, list[Msg]]:
        """Multi hop swap message
        """
        token_in, token_out = self.assertion(token_in, token_out)

        if not isinstance(amount_in, Dec):
            amount_in = to_Dec(amount_in, token_in)

        routing = await self.dijkstra_routing(token_in, amount_in, token_out)
        return await self.route_to_msg(routing)
