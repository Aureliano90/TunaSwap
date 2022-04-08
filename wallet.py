from typing import Dict, List
from terra_sdk.client.lcd import AsyncWallet as _AsyncWallet
from terra_sdk.client.lcd.api.tx import CreateTxOptions, SignerOptions
from terra_sdk.core import Tx
from terra_sdk.core.broadcast import BlockTxBroadcastResult
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
                    task = loop.create_task(_fget(instance), name=f'wallet.{name}')
                    return task
                else:
                    return loop.run_until_complete(_fget(instance))
            return attr

        super().__init__(getter, setter, doc=fget.__doc__)


class AsyncWallet(_AsyncWallet):
    """Custom AsyncWallet initialized by `await AsyncWallet(lcd, key)`\n
    `wallet.sequence` is automatically incremented.
    """
    account_number = async_property(_AsyncWallet.account_number)
    # Nonce
    sequence = async_property(_AsyncWallet.sequence)

    def __init__(self, lcd, key: Key):
        super(AsyncWallet, self).__init__(lcd, key)
        self._account_number = None
        self._sequence = None

    def __await__(self):
        yield from asyncio.create_task(self.account_number_and_sequence())
        return self

    async def account_number_and_sequence(self) -> Dict:
        try:
            res = await super(AsyncWallet, self).account_number_and_sequence()
            self._account_number, self._sequence = res['account_number'], res['sequence']
            return dict(account_number=self.account_number, sequence=self.sequence)
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
            print(f"Exception in wallet.estimate_fee\n{exc}")
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
        if not self.account_number or not self.sequence:
            await self.account_number_and_sequence()
        tx_options = CreateTxOptions(msgs=msgs, **options)
        tx_options.account_number = self.account_number
        tx_options.sequence = self.sequence
        try:
            return await super(AsyncWallet, self).create_and_sign_tx(tx_options)
        except LCDResponseError as exc:
            print(f"Exception in wallet.create_and_sign_tx\n{exc}")
            if 'account sequence mismatch' in exc.message:
                await self.account_number_and_sequence()
                tx_options.sequence = self.sequence
                return await super(AsyncWallet, self).create_and_sign_tx(tx_options)
            return None

    async def broadcast(
            self,
            tx: Tx
    ) -> BlockTxBroadcastResult | None:
        try:
            result = await self.lcd.tx.broadcast(tx)
            if hasattr(result, 'code') and result.code:
                print(f"Transaction failed.\nCode: {result.code} Codespace: {result.codespace}")
                print(f"Raw log: {result.raw_log}")
            else:
                self.sequence = self.sequence + 1
                return result
        except LCDResponseError as exc:
            print(f"Exception in wallet.broadcast\n{exc}")
        return None
