from src.pool import *
from pysondb import getDb
from datetime import datetime, timedelta

txs_db = getDb('txs.json')


class TxResult(BlockTxBroadcastResult):
    @classmethod
    def from_data(cls, tx: Dict):
        return cls(
            tx['height'],
            tx['txhash'],
            tx['raw_log'],
            tx['gas_wanted'],
            tx['gas_used'],
            tx['logs'])


def save_tx(tx: TxResult | TxInfo):
    try:
        data = TxResult.to_data(tx)
        if data:
            if 'code' not in data:
                data['code'], data['codespace'] = 0, ''
            if 'data' not in data:
                data['data'] = None
            if 'info' not in data:
                data['info'] = None
            if 'tx' in data:
                data.pop('tx')
            if 'rawlog' in data:
                data['raw_log'] = data['rawlog']
                data.pop('rawlog')
            txs_db.add(data)
    except Exception as exc:
        print('save_tx', exc)
        # print(tx)


def retrieve_tx(txhash: str) -> TxResult | None:
    for res in txs_db.getByQuery({'txhash': txhash}):
        return TxResult.from_data(res)


def filter_tx_log_by_type(
        log: TxLog,
        event: str,
        conditions: Dict
) -> Dict:
    """Filter transaction log by matching conditions' index
    """
    res = dict()
    index = -1
    for key in conditions:
        values = log.events_by_type[event][key]
        if index == -1:
            for i, value in enumerate(values):
                if value == conditions[key]:
                    index = i
                    break
        else:
            if values[index] != conditions[key]:
                return {}
    if index == -1:
        return {}
    for key, values in log.events_by_type[event].items():
        res[key] = values[index]
    return res


def filter_tx_log_by_order(
        log: TxLog,
        event: str,
        divider: str,
        conditions: Dict
) -> Dict:
    """Filter transaction log by dividing an event into sections
    """
    for e in log.events:
        if e['type'] == event:
            events = e['attributes']
            break
    else:
        return {}
    sections = []
    for i, v in enumerate(events):
        if v['key'] == divider:
            sections.append(i)
    sections.append(len(events))
    for i in range(len(sections) - 1):
        section = {item['key']: item['value'] for item in events[sections[i]:sections[i + 1]]}
        for k, v in conditions.items():
            if k in section:
                if v != section[k]:
                    break
            else:
                break
        else:
            return section
    return {}


def calculate_profit(tx: BlockTxBroadcastResult | TxInfo | TxResult | Dict) -> Coins:
    if isinstance(tx, Dict):
        tx = TxResult.from_data(tx)
    try:
        logs = tx.logs
    except AttributeError:
        return Coins()
    coin_spent = coin_received = token_received = token_spent = Coins()
    for log in logs:
        spent_event = filter_tx_log_by_type(log,
                                            'coin_spent',
                                            {'spender': wallet.key.acc_address})
        if spent_event:
            coin_spent = coin_spent + Coins.from_str(spent_event['amount'])
        received_event = filter_tx_log_by_type(log,
                                               'coin_received',
                                               {'receiver': wallet.key.acc_address})
        if received_event:
            coin_received = coin_received + Coins.from_str(received_event['amount'])
        received_event = filter_tx_log_by_order(log,
                                                'from_contract',
                                                'contract_address',
                                                {'action': 'transfer', 'to': wallet.key.acc_address})
        if received_event:
            token = token_from_contract(received_event['contract_address'])
            token_received = token_received + Coins({token: received_event['amount']})
        spent_event = filter_tx_log_by_order(log,
                                             'from_contract',
                                             'contract_address',
                                             {'action': 'send', 'from': wallet.key.acc_address})
        if spent_event:
            token = token_from_contract(spent_event['contract_address'])
            token_spent = token_spent + Coins({token: spent_event['amount']})
    cost = Coins(uusd=gas_prices['uusd']).get('uusd') * tx.gas_wanted
    coins = coin_received - coin_spent + token_received - token_spent - cost
    return from_Dec(coins)


def sum_profit():
    profit = Coins()
    for tx in txs_db.getAll():
        profit = profit + calculate_profit(tx)
    pprint(profit)


def pool_from_contract(contract: str) -> Pool:
    for pair, dexes in pools_info.items():
        for dex, info in dexes.items():
            if info['contract'] == contract:
                return Pool(pair, dex)


def pools_from_contracts() -> Dict[str, Pool]:
    pools = dict()
    for pair, dexes in pools_info.items():
        for dex, info in dexes.items():
            if 'contract' in info:
                pools[info['contract']] = Pool(pair, dex)
    return pools


async def query_mempool():
    return await fcd._get('/v1/mempool')


pool_contract_map = pools_from_contracts()
msg_types = {MsgExecuteContract.type_amino: MsgExecuteContract,
             MsgSwap.type_amino: MsgSwap}


async def parse_mempool(mempool: Dict, pool_map: Dict[Tuple[Pair, str], Pool]):
    now = datetime.utcnow()
    delta = timedelta(seconds=20)
    for tx_amino in mempool['txs']:
        timestamp = datetime.fromisoformat(tx_amino['timestamp'][:-1])
        if now - timestamp > delta:
            continue
        tx = tx_amino['tx']
        msgs = tx['value']['msg']
        for amino in msgs:
            # print(amino)
            msg = parse_amino(amino)
            if type(msg) in msg_types.values():
                await parse_pool_msg(msg, pool_map)
            # print(msg)


async def parse_pool_msg(msg: Msg, pool_map: Dict[Tuple[Pair, str], Pool]):
    if isinstance(msg, MsgExecuteContract):
        if msg.contract in pool_contract_map:
            pool = pool_contract_map[msg.contract]
            if (pool.pair, pool.dex) in pool_map:
                pool = pool_map[pool.pair, pool.dex]
                # print('simulate_msg', pool)
                await pool.simulate_msg(msg)
    elif isinstance(msg, MsgSwap):
        await pool_map[Pair('luna', 'ust'), 'native_swap'].simulate_msg(msg)


def from_amino(cls, data: dict) -> MsgExecuteContract:
    assert cls.type_amino == data['type']
    data = data['value']
    return cls(
        sender=data['sender'],
        contract=data['contract'],
        execute_msg=parse_msg(data['execute_msg']),
        coins=Coins.from_data(data['coins']),
    )


amino_methods = dict()
amino_methods[MsgExecuteContract.type_amino] = from_amino


def from_amino(cls, data: dict) -> MsgSwap:
    assert cls.type_amino == data['type']
    data = data['value']
    return cls(
        trader=data['trader'],
        offer_coin=Coin.from_data(data['offer_coin']),
        ask_denom=data['ask_denom'],
    )


amino_methods[MsgSwap.type_amino] = from_amino


def parse_amino(data: dict):
    if data['type'] in msg_types:
        return amino_methods[data['type']](msg_types[data['type']], data)
