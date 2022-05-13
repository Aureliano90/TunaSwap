from datetime import datetime
from src.transaction import *
import attr


@attr.s(slots=True)
class Anchor:
    borrowed_value: Dec = attr.ib(default=Dec(0))
    borrow_limit: Dec = attr.ib(default=Dec(0))
    # aUST exchange rate
    exchange_rate: Dec = attr.ib(default=Dec(0))
    # aUST balance
    deposit: Dec = attr.ib(default=Dec(0))
    collaterals: Coins = attr.ib(factory=Coins)
    prices: Dict[str, Dec] = attr.ib(factory=dict)

    def __await__(self):
        yield from asyncio.gather(self.update_loan(),
                                  self.update_collaterals(),
                                  self.update_prices(),
                                  self.deposit_balance())
        return self

    async def update_state(self):
        state = await terra.wasm.contract_query(anchor['market'], ABI.self('state'))
        self.exchange_rate = Dec(state['prev_exchange_rate'])

    async def update_prices(self):
        res = await terra.wasm.contract_query(anchor['oracle'], ABI.self('prices'))
        for feed in res['prices']:
            asset = token_from_contract(feed['asset'])
            if asset:
                self.prices[asset] = Dec(feed['price'])

    async def deposit_balance(self) -> Dec:
        if self.exchange_rate == Dec(0):
            await self.update_state()
        self.deposit = await token_balance('aust')
        return self.deposit

    async def deposit_stable(self, amount: Numeric) -> List[Msg]:
        if self.exchange_rate == Dec(0):
            await self.update_state()
        amount = to_Dec(amount, 'ust')
        self.deposit += amount / self.exchange_rate
        return [MsgExecuteContract(wallet.key.acc_address,
                                   anchor['market'],
                                   ABI.self('deposit_stable'),
                                   Coins({'uusd': amount.whole}))]

    async def redeem_stable(self, amount: Numeric) -> List[Msg]:
        if self.exchange_rate == Dec(0):
            await self.update_state()
        amount = to_Dec(amount, 'ust') / self.exchange_rate
        amount = min(self.deposit, amount)
        self.deposit -= amount
        return [MsgExecuteContract(wallet.key.acc_address,
                                   tokens_info['aust']['contract'],
                                   ABI.send(anchor['market'], amount, ABI.self('redeem_stable')))]

    async def borrow_stable(self, amount: Numeric) -> List[Msg]:
        amount = to_Dec(amount, 'ust')
        self.borrowed_value += amount
        return [MsgExecuteContract(wallet.key.acc_address,
                                   anchor['market'],
                                   ABI.borrow_stable(amount))]

    async def repay_stable(self, amount: Numeric) -> List[Msg]:
        amount = to_Dec(amount, 'ust')
        self.borrowed_value -= amount
        return [MsgExecuteContract(wallet.key.acc_address,
                                   anchor['market'],
                                   ABI.self('repay_stable'),
                                   Coins({'uusd': amount.whole}))]

    async def update_loan(self):
        borrower_info = ABI.multicall_query(anchor['market'], ABI.borrower_info(wallet.key.acc_address))
        borrow_limit = ABI.multicall_query(anchor['overseer'], ABI.borrow_limit(wallet.key.acc_address))
        state = ABI.multicall_query(anchor['market'], ABI.self('state'))
        res = await multicall_query([borrower_info, borrow_limit, state])
        self.borrowed_value = Dec(res[0]['loan_amount'])
        self.borrow_limit = Dec(res[1]['borrow_limit'])
        self.exchange_rate = Dec(res[2]['prev_exchange_rate'])

    async def update_collaterals(self):
        res = await terra.wasm.contract_query(anchor['overseer'], ABI.collaterals(wallet.key.acc_address))
        self.collaterals = Coins()
        for collateral in res['collaterals']:
            self.collaterals = self.collaterals + Coin(token_from_contract(collateral[0]), Dec(collateral[1]))
        print(f"Collaterals: {self.collaterals}")

    async def deposit_collateral(
            self,
            collateral: str,
            amount: Numeric
    ) -> List[Msg]:
        amount = to_Dec(amount, collateral)
        self.collaterals = self.collaterals + Coin(collateral, amount)
        execute_msg = ABI.send(anchor['custody'][collateral], amount, ABI.self('deposit_collateral'))
        deposit_msg = MsgExecuteContract(wallet.key.acc_address,
                                         tokens_info[collateral]['contract'],
                                         execute_msg)
        lock_msg = MsgExecuteContract(wallet.key.acc_address,
                                      anchor['overseer'],
                                      ABI.lock_collateral(collateral, amount))
        return [deposit_msg, lock_msg]

    async def withdraw_collateral(
            self,
            collateral: str,
            amount: Numeric
    ) -> List[Msg]:
        amount = to_Dec(amount, collateral)
        self.collaterals = self.collaterals - Coin(collateral, amount)
        unlock_msg = MsgExecuteContract(wallet.key.acc_address,
                                        anchor['overseer'],
                                        ABI.unlock_collateral(collateral, amount))
        withdraw_msg = MsgExecuteContract(wallet.key.acc_address,
                                          anchor['custody'][collateral],
                                          ABI.withdraw_collateral(amount))
        return [unlock_msg, withdraw_msg]

    async def monitor(self):
        async for _ in wallet.blockchain:
            await self.update_loan()
            if self.borrowed_value < self.borrow_limit * 0.8:
                borrow_amount = self.borrow_limit * 0.85 - self.borrowed_value
                print(f"Current LTV {(self.borrowed_value / self.borrow_limit).to_short_str()} "
                      f"Borrowing {from_Dec(borrow_amount, 'ust')} UST")
                borrow_msg = await self.borrow_stable(borrow_amount)
                deposit_msg = await self.deposit_stable(borrow_amount)
                msgs = borrow_msg + deposit_msg
                res = await wallet.create_and_broadcast(msgs, gas='750000')
            elif self.borrowed_value > self.borrow_limit * 0.9:
                repay_amount = self.borrowed_value - self.borrow_limit * 0.85
                print(f"Current LTV {(self.borrowed_value / self.borrow_limit).to_short_str()} "
                      f"Repaying {from_Dec(repay_amount, 'ust')} UST")
                if self.deposit < to_Dec(1, 'aust'):
                    repay_amount = min(await token_balance('ust') - to_Dec(10, 'ust'), repay_amount)
                    if repay_amount < to_Dec(10, 'ust'):
                        continue
                    msgs = await self.repay_stable(repay_amount)
                else:
                    if repay_amount > self.deposit * self.exchange_rate:
                        repay_amount = await self.deposit_balance() * self.exchange_rate
                    withdraw_msg = await self.redeem_stable(repay_amount)
                    repay_msg = await self.repay_stable(repay_amount)
                    msgs = withdraw_msg + repay_msg
                res = await wallet.create_and_broadcast(msgs, gas='650000')
            else:
                continue
            if res:
                save_tx(res)
                print(f"{datetime.now()} New LTV {(self.borrowed_value / self.borrow_limit).to_short_str()}")
