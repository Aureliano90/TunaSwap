testnet = False
max_spread = 0.15
slippage = 0.005
native_tokens = {'ust', 'luna'}

if testnet:
    tokens_info = {'ust': {'denom': 'uusd', 'decimals': 6,
                           'dex': ('terra_swap', 'astro_swap')},
                   'luna': {'denom': 'uluna', 'decimals': 6,
                            'dex': ('terra_swap', 'astro_swap')},
                   'aust': {'contract': 'terra1ajt556dpzvjwl0kl5tzku3fc3p3knkg9mkv8jl',
                            'decimals': 6, 'dex': ('terra_swap',)},
                   'anc': {'contract': 'terra1747mad58h0w4y589y3sk84r5efqdev9q4r02pc',
                           'decimals': 6, 'dex': ('terra_swap', 'astro_swap')},
                   'bluna': {'contract': 'terra1u0t35drzyy0mujj8rkdyzhe264uls4ug3wdp3x',
                             'decimals': 6, 'dex': ('terra_swap', 'astro_swap')},
                   'stluna': {'contract': 'terra1e42d7l5z5u53n7g990ry24tltdphs9vugap8cd',
                              'decimals': 6, 'dex': ('astro_swap',)},
                   'psi': {'contract': 'terra18nle009rtynpjgleh2975rleu5zts0zdtqryte',
                           'decimals': 6, 'dex': ('terra_swap', 'astro_swap')},
                   'nluna': {'contract': 'terra1gzq2zd4skvnvgm2z48fdp0mxy2djmtk7sz4uhe',
                             'decimals': 6, 'dex': ('astro_swap',)},
                   'astro': {'contract': 'terra1jqcw39c42mf7ngq4drgggakk3ymljgd3r5c3r5',
                             'decimals': 6, 'dex': ('astro_swap',)},
                   'mine': {'contract': 'terra1lqm5tutr5xcw9d5vc4457exa3ghd4sr9mzwdex',
                            'decimals': 6, 'dex': ('astro_swap',)},
                   'mars': {'contract': 'terra1qs7h830ud0a4hj72yr8f7jmlppyx7z524f7gw6',
                            'decimals': 6, 'dex': ('astro_swap',)},
                   'kuji': {'contract': 'terra1azu2frwn9a4l6gl5r39d0cuccs4h7xlu9gkmtd',
                            'decimals': 6, 'dex': ('astro_swap',)},
                   }
else:
    tokens_info = {'ust': {'denom': 'uusd', 'decimals': 6,
                           'dex': ('terra_swap', 'astro_swap', 'loop')},
                   'luna': {'denom': 'uluna', 'decimals': 6,
                            'dex': ('terra_swap', 'astro_swap', 'loop')},
                   'aust': {'contract': 'terra1hzh9vpxhsk8253se0vv5jj6etdvxu3nv8z07zu',
                            'decimals': 6, 'dex': ('terra_swap', 'loop')},
                   'anc': {'contract': 'terra14z56l0fp2lsf86zy3hty2z47ezkhnthtr9yq76',
                           'decimals': 6, 'dex': ('terra_swap', 'astro_swap', 'loop')},
                   'bluna': {'contract': 'terra1kc87mu460fwkqte29rquh4hc20m54fxwtsx7gp',
                             'decimals': 6, 'dex': ('terra_swap', 'astro_swap', 'loop')},
                   'stluna': {'contract': 'terra1yg3j2s986nyp5z7r2lvt0hx3r0lnd7kwvwwtsc',
                              'decimals': 6, 'dex': ('astro_swap',)},
                   'lunax': {'contract': 'terra17y9qkl8dfkeg4py7n0g5407emqnemc3yqk5rup',
                              'decimals': 6, 'dex': ('terra_swap', 'loop')},
                   'bpsidp-24m': {'contract': 'terra1zsaswh926ey8qa5x4vj93kzzlfnef0pstuca0y',
                                  'decimals': 6, 'dex': ('terra_swap',)},
                   'psi': {'contract': 'terra12897djskt9rge8dtmm86w654g7kzckkd698608',
                           'decimals': 6, 'dex': ('terra_swap', 'astro_swap')},
                   'nluna': {'contract': 'terra10f2mt82kjnkxqj2gepgwl637u2w4ue2z5nhz5j',
                             'decimals': 6, 'dex': ('terra_swap', 'astro_swap')},
                   'astro': {'contract': 'terra1xj49zyqrwpv5k928jwfpfy2ha668nwdgkwlrg3',
                             'decimals': 6, 'dex': ('astro_swap',)},
                   'mine': {'contract': 'terra1kcthelkax4j9x8d3ny6sdag0qmxxynl3qtcrpy',
                            'decimals': 6, 'dex': ('astro_swap',)},
                   'mars': {'contract': 'terra12hgwnpupflfpuual532wgrxu2gjp0tcagzgx4n',
                            'decimals': 6, 'dex': ('astro_swap',)},
                   'kuji': {'contract': 'terra1xfsdgcemqwxp4hhnyk4rle6wr22sseq7j07dnn',
                            'decimals': 6, 'dex': ('terra_swap', 'loop')},
                   }


class Pair:
    def __init__(self, token1: str, token2: str):
        self.pair = {token1.lower(), token2.lower()}

    def other(self, token):
        """The other token in the pair
        """
        return [i for i in self.pair if i != token][0]

    def __repr__(self):
        return f'Pair{tuple(sorted(self.pair))}'

    def __eq__(self, other):
        return True if self.pair == other.pair else False

    def __hash__(self):
        return hash(tuple(sorted(self.pair)))


if testnet:
    # Router contract
    router = {'terra_swap': 'terra14z80rwpd0alzj4xdtgqdmcqt9wd9xj5ffd60wp',
             'astro_swap': 'terra13wf295fj9u209nknz2cgqmmna7ry3d3j5kv7t4'}

    # Factory contract
    factory = {'terra_swap': 'terra18qpjm4zkvqnpjpw0zn0tdr8gdzvt8au35v45xf',
               'astro_swap': 'terra15jsahkaf9p0qu8ye873p0u5z6g07wdad0tdq43'}

    assert_limit_order = 'terra1z3sf42ywpuhxdh78rr5vyqxpaxa0dx657x5trs'

    # https://finder.extraterrestrial.money/testnet/projects/terraswap
    # https://finder.extraterrestrial.money/testnet/projects/terraswap
    pools_info = {
        Pair('luna', 'ust'): {
            'terra_swap': {'contract': 'terra156v8s539wtz0sjpn8y8a8lfg8fhmwa7fy22aff',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
            'astro_swap': {'contract': 'terra1e49fv4xm3c2znzpxmxs0z2z6y74xlwxspxt38s',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
            'native_swap': {}
        },
        Pair('bluna', 'luna'): {
            'terra_swap': {'contract': 'terra13e4jmcjnwrauvl2fnjdwex0exuzd8zrh5xk29v',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
            'astro_swap': {'contract': 'terra1esle9h9cjeavul53dqqws047fpwdhj6tynj5u4',
                           'fee': 0.0005, 'tx_fee': 0, 'stable': True}
        },
        Pair('stluna', 'luna'): {
            'astro_swap': {'contract': 'terra1cx2rqwsgsdhg3t9ce3kef33dncaswknemucrzf',
                           'fee': 0.0005, 'tx_fee': 0, 'stable': True}},
        Pair('anc', 'ust'): {
            'terra_swap': {'contract': 'terra1wfvczps2865j0awnurk9m04u7wdmd6qv3fdnvz',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
            'astro_swap': {'contract': 'terra13r3vngakfw457dwhw9ef36mc8w6agggefe70d9',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}
        },
        Pair('psi', 'ust'): {
            'terra_swap': {'contract': 'terra1ee9h9c9fv2smm8wkq0aw78tut3w3x62ckj6nz8',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
            'astro_swap': {'contract': 'terra1a7vcghx2vjyg74nqk5krd9ppa8ks8ytz5vdsgp',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}
        },
        Pair('nluna', 'psi'): {
            'astro_swap': {'contract': 'terra1uwf0yn9rnt7anpceqm7s00zfgevnwaaqde2eee',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}
        },
        Pair('astro', 'ust'): {
            'astro_swap': {'contract': 'terra1ec0fnjk2u6mms05xyyrte44jfdgdaqnx0upesr',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}
        },
        Pair('mine', 'ust'): {
            'terra_swap': {'contract': 'terra1n2xmlwqpp942nfqq2muxn0u0mqk3sylekdpqfv',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
            'astro_swap': {'contract': 'terra1hh20kjfz4yaqkyfwfd2n8ktwnr956m82r9lqd4',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}
        },
        Pair('mars', 'ust'): {
            'astro_swap': {'contract': 'terra1z7250szwg9khf20a72r2u7qv2l4ndghkhhp4ev',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}
        },
        Pair('kuji', 'ust'): {
            'astro_swap': {'contract': 'terra178na9upyad7gu4kulym9uamwafgrf922yln76l',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}
        },
    }
else:
    # Router contract
    router = {'terra_swap': 'terra19qx5xe6q9ll4w0890ux7lv2p4mf3csd4qvt3ex',
             'astro_swap': 'terra16t7dpwwgx9n3lq6l6te3753lsjqwhxwpday9zx'}

    # Factory contract
    factory = {'terra_swap': 'terra1ulgw0td86nvs4wtpsc80thv6xelk76ut7a7apj',
               'astro_swap': 'terra1fnywlw4edny3vw44x04xd67uzkdqluymgreu7g',
               'loop': 'terra16hdjuvghcumu6prg22cdjl96ptuay6r0hc6yns'}

    # https://finder.extraterrestrial.money/mainnet/projects/terraswap
    # https://finder.extraterrestrial.money/mainnet/projects/astroport
    # https://coinhall.org/
    pools_info = {
        Pair('luna', 'ust'): {
            'terra_swap': {'contract': 'terra1tndcaqxkpc5ce9qee5ggqf430mr2z3pefe5wj6',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
            'astro_swap': {'contract': 'terra1m6ywlgn6wrjuagcmmezzz2a029gtldhey5k552',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
            'native_swap': {},
            'loop': {'contract': 'terra1sgu6yca6yjk0a34l86u6ju4apjcd6refwuhgzv',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}
        },
        Pair('aust', 'ust'): {
            'terra_swap': {'contract': 'terra1z50zu7j39s2dls8k9xqyxc89305up0w7f7ec3n',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
            'loop': {'contract': 'terra123neekasfmvcs4wa70cgw3j3uvwzqacdz2we03',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}},
        Pair('aust', 'luna'): {
            'loop': {'contract': 'terra16j5f4lp4z8dddm3rhyw8stwrktyhcsc8ll6xtt',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}},
        Pair('bluna', 'luna'): {
            'terra_swap': {'contract': 'terra1jxazgm67et0ce260kvrpfv50acuushpjsz2y0p',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
            'astro_swap': {'contract': 'terra1j66jatn3k50hjtg2xemnjm8s7y8dws9xqa5y8w',
                           'fee': 0.0005, 'tx_fee': 0, 'stable': True},
            'loop': {'contract': 'terra1v93ll6kqp33unukuwls3pslquehnazudu653au',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}
        },
        Pair('bluna', 'ust'): {
            'terra_swap': {'contract': 'terra1qpd9n7afwf45rkjlpujrrdfh83pldec8rpujgn',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
            'loop': {'contract': 'terra18r6rdnkgrg74zew3d8l9nhk0m4xanpeukw3e20',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}},
        Pair('stluna', 'luna'): {
            'astro_swap': {'contract': 'terra1gxjjrer8mywt4020xdl5e5x7n6ncn6w38gjzae',
                           'fee': 0.0005, 'tx_fee': 0, 'stable': True}},
        Pair('lunax', 'luna'): {
            'terra_swap': {'contract': 'terra1zrzy688j8g6446jzd88vzjzqtywh6xavww92hy',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
            'loop': {'contract': 'terra1ga8dcmurj8a3hd4vvdtqykjq9etnw5sjglw4rg',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}},
        Pair('lunax', 'ust'): {
            'terra_swap': {'contract': 'terra1llhpkqd5enjfflt27u3jx0jcp5pdn6s9lfadx3',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
            'loop': {'contract': 'terra1xew5epfvlzqc9zz8urhupnql5k2wls0p5dd0rg',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}
        },
        Pair('anc', 'ust'): {
            'terra_swap': {'contract': 'terra1gm5p3ner9x9xpwugn9sp6gvhd0lwrtkyrecdn3',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
            'astro_swap': {'contract': 'terra1qr2k6yjjd5p2kaewqvg93ag74k6gyjr7re37fs',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
            'loop': {'contract': 'terra1f6d3pggq7h2y7jrgwxp3xh08yhvj8znalql87h',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}
        },
        Pair('bpsidp-24m', 'psi'): {
            'terra_swap': {'contract': 'terra167gwjhv4mrs0fqj0q5tejyl6cz6qc2cl95z530',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}},
        Pair('psi', 'ust'): {
            'terra_swap': {'contract': 'terra163pkeeuwxzr0yhndf8xd2jprm9hrtk59xf7nqf',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
            'astro_swap': {'contract': 'terra1v5ct2tuhfqd0tf8z0wwengh4fg77kaczgf6gtx',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}
        },
        Pair('nluna', 'psi'): {
            'astro_swap': {'contract': 'terra10lv5wz84kpwxys7jeqkfxx299drs3vnw0lj8mz',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
            'terra_swap': {'contract': 'terra1zvn8z6y8u2ndwvsjhtpsjsghk6pa6ugwzxp6vx',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}
        },
        Pair('astro', 'ust'): {
            'astro_swap': {'contract': 'terra1l7xu2rl3c7qmtx3r5sd2tz25glf6jh8ul7aag7',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}
        },
        Pair('mine', 'ust'): {
            'astro_swap': {'contract': 'terra134m8n2epp0n40qr08qsvvrzycn2zq4zcpmue48',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}
        },
        Pair('mars', 'ust'): {
            'astro_swap': {'contract': 'terra19wauh79y42u5vt62c5adt2g5h4exgh26t3rpds',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}
        },
        Pair('kuji', 'ust'): {
            'terra_swap': {'contract': 'terra1zkyrfyq7x9v5vqnnrznn3kvj35az4f6jxftrl2',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
            'loop': {'contract': 'terra1wh2jqjkagzyd3yl4sddlapy45ry808xe80fchh',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}
        },
        Pair('kuji', 'aust'): {
            'loop': {'contract': 'terra1l60336rkawujnwk7lgfq5u0s684r99p3y8hx65',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
        }
    }
