testnet = True
max_spread = 0.5
slippage = 0.001
native_tokens = {'ust', 'luna'}

if testnet:
    tokens_info = {'ust': {'denom': 'uusd', 'decimals': 6,
                           'dex': ('terra_swap', 'astro_swap', 'prism_swap')},
                   'luna': {'denom': 'uluna', 'decimals': 6,
                            'dex': ('terra_swap', 'astro_swap', 'prism_swap')},
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
                   'prism': {'contract': 'terra1cwle4remlf03mucutzhxfayvmdqsulx8xaahvy',
                             'decimals': 6, 'dex': ('prism_swap',)},
                   'neb': {'contract': 'terra1aj5yepjnmhdvh0xz3dfqeh30wday6tapvaze47',
                           'decimals': 6, 'dex': ('astro_swap',)},
                   'batom': {'contract': 'terra1pw8kuxf3d7xnlsrqr39p29emwvufyr0yyjk3fg',
                             'decimals': 6, 'dex': ('astro_swap',)},
                   }
else:
    tokens_info = {'ust': {'denom': 'uusd', 'decimals': 6,
                           'dex': ('terra_swap', 'astro_swap', 'prism_swap', 'loop')},
                   'luna': {'denom': 'uluna', 'decimals': 6,
                            'dex': ('terra_swap', 'astro_swap', 'prism_swap', 'loop')},
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
                   'prism': {'contract': 'terra1dh9478k2qvqhqeajhn75a2a7dsnf74y5ukregw',
                             'decimals': 6, 'dex': ('prism_swap',)},
                   'batom': {'contract': 'terra18zqcnl83z98tf6lly37gghm7238k7lh79u4z9a',
                             'decimals': 6, 'dex': ()},
                   'atom': {'denom': 'ibc/18ABA66B791918D51D33415DA173632735D830E2E77E63C91C11D3008CFD5262',
                            'decimals': 6, 'dex': ()},
                   }


class Pair:
    __slots__ = 'pair'

    def __init__(self, token1: str, token2: str):
        self.pair = tuple(sorted([token1.lower(), token2.lower()]))

    def other(self, token):
        """The other token in the pair
        """
        return [i for i in self.pair if i != token][0]

    def __repr__(self):
        return f"Pair{self.pair}"

    def __eq__(self, other):
        return self.pair == other.pair

    def __hash__(self):
        return hash(self.pair)


if testnet:
    multicall = 'terra1z9p02s5fkasx5qxdaes6mfyf2gt3kxuhcsd4va'

    dexes = {'native_swap', 'terra_swap', 'astro_swap', 'prism_swap'}

    # Router contract
    router = {'terra_swap': 'terra14z80rwpd0alzj4xdtgqdmcqt9wd9xj5ffd60wp',
              'astro_swap': 'terra13wf295fj9u209nknz2cgqmmna7ry3d3j5kv7t4',
              'prism_swap': 'terra1hn2dlykp8k5uspy6np5ks27060wnav6stmpvm5'}

    # Factory contract
    factory = {'terra_swap': 'terra18qpjm4zkvqnpjpw0zn0tdr8gdzvt8au35v45xf',
               'astro_swap': 'terra15jsahkaf9p0qu8ye873p0u5z6g07wdad0tdq43',
               'prism_swap': 'terra1g6x8r77h7sywyxc8zgfdyh39y770nvdm0vnl0r'}

    assert_limit_order = 'terra1z3sf42ywpuhxdh78rr5vyqxpaxa0dx657x5trs'

    anchor = {
        'market': 'terra15dwd5mj8v59wpj0wvt233mf5efdff808c5tkal',
        'oracle': 'terra1p4gg3p2ue6qy2qfuxtrmgv2ec3f4jmgqtazum8',
        'overseer': 'terra1qljxd0y3j3gk97025qvl3lgq8ygup4gsksvaxv',
        'custody': {
            'bluna': 'terra1ltnkx0mv7lf2rca9f8w740ashu93ujughy4s7p',
            'batom': 'terra1e0s58n8grearn5nj7dz8tjrmq5hpqkeatxuhc3'
        }
    }

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
            'terra_swap': {'contract': 'terra1mxy8lmf2jeyr7js7xvm046fssyfa5a9pm78fpn',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
            'astro_swap': {'contract': 'terra178na9upyad7gu4kulym9uamwafgrf922yln76l',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}
        },
        Pair('neb', 'ust'): {
            'astro_swap': {'contract': 'terra1u6tn733n3hw2gzkhqmqurajxjggfvf45qujq3d',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False}
        },
        Pair('prism', 'ust'): {
            'prism_swap': {'contract': 'terra1lveas7a5k3ghxmn9gjn584pfpv7644fyuhhdv3',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
        },
        Pair('prism', 'luna'): {
            'prism_swap': {'contract': 'terra1dhgw7ra0hajtn3smy4uvkyr7e6utewlw7afnly',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
        },
        Pair('batom', 'ust'): {
            'astro_swap': {'contract': 'terra1xu2r64k7ffwqv5pzq6fxupglg5tthwr68t9lwc',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
        },
    }
else:
    multicall = 'terra1y60jx2jqh5qpmcnvgz3n0zg2p6ky4mr6ax2qa5'

    dexes = {'native_swap', 'terra_swap', 'astro_swap', 'prism_swap', 'loop'}

    # Router contract
    router = {'terra_swap': 'terra19qx5xe6q9ll4w0890ux7lv2p4mf3csd4qvt3ex',
              'astro_swap': 'terra16t7dpwwgx9n3lq6l6te3753lsjqwhxwpday9zx',
              'prism_swap': 'terra1yrc0zpwhuqezfnhdgvvh7vs5svqtgyl7pu3n6c'}

    # Factory contract
    factory = {'terra_swap': 'terra1ulgw0td86nvs4wtpsc80thv6xelk76ut7a7apj',
               'astro_swap': 'terra1fnywlw4edny3vw44x04xd67uzkdqluymgreu7g',
               'prism_swap': 'terra1sfw7vvwhsczkeje22ramy76pj5cm9gtvvnzn94',
               'loop': 'terra16hdjuvghcumu6prg22cdjl96ptuay6r0hc6yns'}

    assert_limit_order = 'terra1vs9jr7pxuqwct3j29lez3pfetuu8xmq7tk3lzk'

    anchor = {
        'market': 'terra1sepfj7s0aeg5967uxnfk4thzlerrsktkpelm5s',
        'oracle': 'terra1cgg6yef7qcdm070qftghfulaxmllgmvk77nc7t',
        'overseer': 'terra1tmnqgvg567ypvsvk6rwsga3srp7e3lg6u0elp8',
        'custody': {
            'bluna': 'terra1ptjp2vfjrwh0j0faj9r6katm640kgjxnwwq9kn',
            'batom': 'terra1zdxlrtyu74gf6pvjkg9t22hentflmfcs86llva'
        }
    }

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
        },
        Pair('prism', 'ust'): {
            'prism_swap': {'contract': 'terra19d2alknajcngdezrdhq40h6362k92kz23sz62u',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
        },
        Pair('prism', 'luna'): {
            'prism_swap': {'contract': 'terra1r38qlqt69lez4nja5h56qwf4drzjpnu8gz04jd',
                           'fee': 0.003, 'tx_fee': 0, 'stable': False},
        },
    }
