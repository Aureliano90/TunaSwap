from src.terra import *
from pysondb import getDb

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
    index = -1
    events_by_type = log.events_by_type[event]
    for key, value in conditions.items():
        try:
            if index == -1:
                index = events_by_type[key].index(value)
            else:
                if index != events_by_type[key].index(value):
                    return {}
        except ValueError:
            return {}
    else:
        return {key: values[index] for key, values in events_by_type.items()}


def filter_tx_log_by_order(
        log: TxLog,
        event: str,
        divider: str,
        conditions: Dict
) -> Dict:
    """Filter transaction log by dividing an event into sections
    """
    events = [e['attributes'] for e in log.events if e['type'] == event]
    if events:
        events = events[0]
        sections = [i for i, v in enumerate(events) if v['key'] == divider] + [len(events)]
        for i in range(len(sections) - 1):
            section = {item['key']: item['value'] for item in events[sections[i]:sections[i + 1]]}
            if all([section.get(k) == v for k, v in conditions.items()]):
                return section
    return {}


def calculate_profit(tx: BlockTxBroadcastResult | TxInfo | TxResult | Dict) -> Coins:
    if isinstance(tx, Dict):
        tx = TxResult.from_data(tx)
    try:
        logs = tx.logs
    except AttributeError:
        return Coins()
    coin_spent, coin_received, token_received, token_spent = Coins(), Coins(), Coins(), Coins()
    for log in logs:
        spent_event = filter_tx_log_by_type(log,
                                            'coin_spent',
                                            {'spender': wallet.key.acc_address})
        if spent_event:
            coin_spent += Coins.from_str(spent_event['amount'])
        received_event = filter_tx_log_by_type(log,
                                               'coin_received',
                                               {'receiver': wallet.key.acc_address})
        if received_event:
            coin_received += Coins.from_str(received_event['amount'])
        received_event = filter_tx_log_by_order(log,
                                                'from_contract',
                                                'contract_address',
                                                {'action': 'transfer', 'to': wallet.key.acc_address})
        if received_event:
            token = token_from_contract(received_event['contract_address'])
            token_received += Coins({token: received_event['amount']})
        spent_event = filter_tx_log_by_order(log,
                                             'from_contract',
                                             'contract_address',
                                             {'action': 'send', 'from': wallet.key.acc_address})
        if spent_event:
            token = token_from_contract(spent_event['contract_address'])
            token_spent += Coins({token: spent_event['amount']})
    if hasattr(tx, 'tx'):
        cost = tx.tx.auth_info.fee.amount
    else:
        cost = Coins(gas_prices).get('uusd') * tx.gas_wanted
    coins = coin_received - coin_spent + token_received - token_spent - cost
    return from_Dec(coins)


def sum_profit():
    profit = Coins()
    for tx in txs_db.getAll():
        profit = profit + calculate_profit(tx)
    pprint(profit)
