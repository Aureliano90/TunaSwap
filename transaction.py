from terra_sdk.core.broadcast import BlockTxBroadcastResult as _BlockTxBroadcastResult
from terra import *


class BlockTxBroadcastResult(_BlockTxBroadcastResult):
    @classmethod
    def from_json(cls, tx: Dict):
        return cls(tx['height'], tx['txhash'], tx['raw_log'], tx['gas_wanted'], tx['gas_used'], tx['logs'])


def save_tx(tx: BlockTxBroadcastResult):
    with open('txs', 'a') as f:
        if tx:
            f.write(tx.to_json() + '\n')


def retrieve_tx(txhash: str):
    with open('txs') as f:
        for tx in f.readlines():
            tx = json.loads(tx)
            if tx['txhash'] == txhash:
                return BlockTxBroadcastResult.from_json(tx)
    return None


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


def calculate_profit(tx: BlockTxBroadcastResult) -> Coins:
    if isinstance(tx, dict):
        tx = BlockTxBroadcastResult.from_json(tx)
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
            token = from_contract(received_event['contract_address'])
            token_received = token_received + Coins({token: received_event['amount']})
        spent_event = filter_tx_log_by_order(log,
                                             'from_contract',
                                             'contract_address',
                                             {'action': 'send', 'from': wallet.key.acc_address})
        if spent_event:
            token = from_contract(spent_event['contract_address'])
            token_spent = token_spent + Coins({token: spent_event['amount']})
    cost = Coins(uusd=gas_prices['uusd']).get('uusd') * tx.gas_wanted
    profit = coin_received - coin_spent + token_received - token_spent - cost
    return profit


def sum_profit():
    profit = Coins()
    with open('txs') as f:
        for tx in f.readlines():
            tx = json.loads(tx)
            profit = profit + calculate_profit(tx)
    pprint(profit)
