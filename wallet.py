from typing import Dict, List
from terra_sdk.client.lcd import AsyncLCDClient, AsyncWallet as _AsyncWallet
from terra_sdk.client.lcd.api.tx import CreateTxOptions, SignerOptions
from terra_sdk.core import Tx, TxInfo
from terra_sdk.core.broadcast import BlockTxBroadcastResult, AsyncTxBroadcastResult
from terra_sdk.core.fee import Fee
from terra_sdk.core.msg import Msg
from terra_sdk.exceptions import LCDResponseError
from terra_sdk.key.key import Key
import asyncio


class async_property(property):
    """Descriptor for the async version of property
    """

    def __init__(self, fget):
        name = fget.__name__
        _name = f'_{name}'

        def setter(instance, value):
            setattr(instance, _name, value)

        async def _fget(instance):
            coro = fget(instance)
            setter(instance, await coro)
            return getattr(instance, _name)

        def getter(instance):
            attr = getattr(instance, _name, False)
            if not attr:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    task = loop.create_task(_fget(instance), name=f'{type(instance).__name__}.{name}')
                    return task
                else:
                    return loop.run_until_complete(_fget(instance))
            return attr

        super().__init__(getter, setter, doc=fget.__doc__)


class BlockChain:
    def __init__(self, lcd: AsyncLCDClient):
        self.lcd = lcd
        self.current_height = 0
        self.new_block_evt = asyncio.Event()

    async def block_height(self):
        """Self-explanatory
        """
        try:
            return int((await self.lcd.tendermint.block_info())['block']['header']['height'])
        except LCDResponseError:
            return 0

    async def set_new_block(self):
        new_height = await self.block_height()
        if new_height > self.current_height:
            if not self.new_block_evt.is_set():
                self.new_block_evt.set()
                self.current_height = new_height

    async def __aiter__(self):
        """AsyncGenerator iterating over blocks
        """
        loop = asyncio.get_event_loop()
        block_time = loop.time()
        self.current_height = await self.block_height()
        yield self.current_height
        while True:
            await asyncio.sleep(6 - loop.time() + block_time)
            self.new_block_evt.clear()
            try:
                while not self.new_block_evt.is_set():
                    asyncio.create_task(self.set_new_block())
                    await asyncio.sleep(0.05)
                block_time = loop.time()
                yield self.current_height
            except LCDResponseError:
                pass


class AsyncWallet(_AsyncWallet):
    """Custom AsyncWallet initialized by `await AsyncWallet(lcd, key)`\n
    `wallet.sequence` is automatically incremented.
    """
    account_number = async_property(_AsyncWallet.account_number)
    # Nonce
    sequence = async_property(_AsyncWallet.sequence)

    def __init__(self, lcd: AsyncLCDClient, key: Key):
        self._account_number = None
        self._sequence = None
        self.blockchain = BlockChain(lcd)
        self.lcd = lcd
        self.key = key

    def __await__(self):
        yield from asyncio.create_task(self.account_number_and_sequence())
        return self

    async def account_number_and_sequence(self) -> Dict:
        try:
            res = await super(AsyncWallet, self).account_number_and_sequence()
            self._account_number, self._sequence = res['account_number'], res['sequence']
            return res
        except LCDResponseError as exc:
            if 'key not found' in exc.message:
                print('Fund address to generate account.')
                # https://faucet.terra.money/
            else:
                raise

    async def estimate_fee(
            self,
            msgs: List[Msg],
            **options
    ) -> Fee | None:
        """Estimate gas fee
        """
        sigOpt = [
            SignerOptions(
                address=self.key.acc_address,
                sequence=self.sequence,
                public_key=self.key.public_key,
            )]
        try:
            return await self.lcd.tx.estimate_fee(sigOpt, CreateTxOptions(msgs=msgs, **options))
        except LCDResponseError as exc:
            print(f"Exception in {type(self).__name__}.estimate_fee\n{exc}")
            if 'account sequence mismatch' in exc.message:
                await self.account_number_and_sequence()
                sigOpt[0].sequence = self.sequence
                return await self.lcd.tx.estimate_fee(sigOpt, CreateTxOptions(msgs=msgs, **options))
            return None

    async def create_and_sign_tx(
            self,
            msgs: List[Msg],
            **options: Dict
    ) -> Tx | None:
        """Self-explanatory
        """
        if not self.account_number or not self.sequence:
            await self.account_number_and_sequence()
        tx_options = CreateTxOptions(msgs=msgs, **options)
        tx_options.account_number = self.account_number
        tx_options.sequence = self.sequence
        try:
            return await super(AsyncWallet, self).create_and_sign_tx(tx_options)
        except LCDResponseError as exc:
            print(f"Exception in {type(self).__name__}.create_and_sign_tx\n{exc}")
            if 'account sequence mismatch' in exc.message:
                await self.account_number_and_sequence()
                tx_options.sequence = self.sequence
                return await super(AsyncWallet, self).create_and_sign_tx(tx_options)
            return None

    async def broadcast(
            self,
            tx: Tx
    ) -> BlockTxBroadcastResult | TxInfo | None:
        """Broadcast and wait for result
        """
        try:
            self.sequence += 1
            result: BlockTxBroadcastResult = await self.lcd.tx.broadcast(tx)
            if hasattr(result, 'code') and result.code:
                self.sequence -= 1
                print(f"Transaction failed.\nCode: {result.code} Codespace: {result.codespace}")
                print(f"Raw log: {result.raw_log}")
                return None
            else:
                return result
        except LCDResponseError as exc:
            print(f"Exception in {type(self).__name__}.broadcast\n{exc}")
            return await self.tx_info(await self.lcd.tx.hash(tx))

    async def tx_info(
            self,
            tx_hash: str
    ) -> TxInfo | None:
        code = 504
        while code == 504:
            try:
                result: TxInfo = await self.lcd.tx.tx_info(tx_hash)
                if hasattr(result, 'code') and result.code:
                    self.sequence -= 1
                    print(f"Transaction failed.\nCode: {result.code} Codespace: {result.codespace}")
                    print(f"Raw log: {result.rawlog}")
                    return None
                else:
                    return result
            except LCDResponseError as exc:
                code = int(exc.response.status)

    async def broadcast_async(
            self,
            tx: Tx
    ) -> AsyncTxBroadcastResult:
        """Broadcast and don't wait
        """
        try:
            self.sequence += 1
            return await self.lcd.tx.broadcast_async(tx)
        except LCDResponseError as exc:
            print(f"Exception in {type(self).__name__}.broadcast_async\n{exc}")
