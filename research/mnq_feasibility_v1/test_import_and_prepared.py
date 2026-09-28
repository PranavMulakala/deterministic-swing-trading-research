import copy
import json
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0,str(Path(__file__).parent))
import engine
from import_databento import DTYPE, normalize, np
from replay_prepared import replay
from .fixture import dataset

CFG=json.loads((Path(__file__).parent/'config.json').read_text())


def prepared(data,cfg,override=None):
    lookup={s['date']:s for s in data['sessions']};result=[]
    for session in data['sessions']:
        sigs,note=engine.signals(session,lookup.get(session.get('previous_date')),cfg)
        if override is not None:sigs=override.get(session['date'],[])
        quotes=[x for x in session['events'] if x['type']=='quote']
        result.append(dict(date=session['date'],signals=sigs,note=note,quotes=quotes,times=[q['ts_ns'] for q in quotes]))
    return result


class AdapterTests(unittest.TestCase):
    def raw(self):
        a=np.zeros(4,dtype=DTYPE)
        for field,value in [('length',20),('rtype',1),('publisher_id',1),('instrument_id',42004800),('price',25000000000),('size',2),('bid_px_00',24750000000),('ask_px_00',25000000000),('bid_sz_00',3),('ask_sz_00',4)]:a[field]=value
        a['ts_event']=[99,100,100,101];a['ts_recv']=[100,101,101,102]
        a['action']=[b'T',b'T',b'C',b'A'];a['flags']=[128,0,128,128]
        a['sequence']=[5,6,6,7]
        return a

    def test_trade_once_and_only_completed_quotes(self):
        t,q,n=normalize(self.raw(),50,100,102)
        self.assertEqual(n,1)
        self.assertEqual(t['seq'].tolist(),[102])
        self.assertEqual(t['price_ticks'].tolist(),[100])
        self.assertEqual(q['seq'].tolist(),[105,107])
        self.assertEqual(q['source_sequence'].tolist(),[6,7])

    def test_split_blocks_preserve_ids_and_boundaries(self):
        a=self.raw();t,q,n=normalize(a,0,100,102)
        left=normalize(a[:2],0,100,102);right=normalize(a[2:],2,100,102)
        np.testing.assert_array_equal(t,np.concatenate([left[0],right[0]]))
        np.testing.assert_array_equal(q,np.concatenate([left[1],right[1]]))

    def test_flagged_unknown_or_off_tick_fails_closed(self):
        for field,value in [('flags',8),('flags',4),('flags',32),('action',b'X'),('price',25000000001),('size',0),('instrument_id',123)]:
            a=self.raw();a[field][1]=value
            with self.assertRaises((ValueError,AssertionError)):normalize(a,0,100,102)

    def test_undefined_quote_is_preserved_as_invalid(self):
        a=self.raw();a['bid_px_00'][2]=9223372036854775807
        _,q,_=normalize(a,0,100,102)
        self.assertEqual(int(q['bid_ticks'][0]),0)

    def equivalent(self,data,cfg,cost,override=None):
        a=engine.replay(data,cfg,cost,override)
        b=replay(prepared(data,cfg,override),cfg,cost)
        self.assertEqual({k:v for k,v in a.items() if k!='equity'}, {k:v for k,v in b.items() if k!='equity'})
        # All retained indexed marks must appear, in order, in the reference marks.
        j=0
        for item in b['equity']:
            while j<len(a['equity']) and a['equity'][j]!=item:j+=1
            self.assertLess(j,len(a['equity']));j+=1

    def test_full_signal_fixture_all_costs_and_mirrored(self):
        for mirror in [False,True]:
            data=dataset()
            if mirror:
                for s in data['sessions']:
                    for e in s['events']:
                        if e['type']=='trade':e['price_ticks']=80000-e['price_ticks']
                        else:e['bid_ticks'],e['ask_ticks']=80000-e['ask_ticks'],80000-e['bid_ticks']
            for cost in CFG['scenarios']:self.equivalent(data,CFG,cost)

    def test_random_quotes_multiday_pauses_latency_and_empty_data(self):
        for seed in range(20):
            rng=random.Random(seed);data=dict(sessions=[]);override={}
            cfg=copy.deepcopy(CFG)
            cfg['drawdown_fraction']=.005
            for day in ['2026-09-03','2026-09-04']:
                start=engine.timestamp(day,10);current=start;price=100;quotes=[]
                for i in range(300):
                    current+=rng.choice([50_000_000,100_000_000,400_000_000,2_000_000_000])
                    price=max(40,price+rng.randint(-15,15))
                    quotes.append(dict(type='quote',ts_ns=current,seq=i,bid_ticks=price,ask_ticks=price+rng.choice([1,1,1,8]),bid_size=rng.choice([0,1,1,1]),ask_size=1))
                data['sessions'].append(dict(date=day,contract='MNQU6',previous_date=None,events=quotes))
                sigs=[]
                for i in [5,6,30,60,100,200]:
                    direction=rng.choice([-1,1]);p=quotes[i]['bid_ticks']
                    sigs.append(dict(id=f'{day}:{i}',day=day,contract='MNQU6',signal_ns=quotes[i]['ts_ns']-1_000_000_000,direction=direction,stop_ticks=p-direction*8,target_ticks=p+direction*30))
                override[day]=sigs
            for cost in CFG['scenarios']:self.equivalent(data,cfg,cost,override)
        self.equivalent(dict(sessions=[]),CFG,CFG['scenarios'][0])


if __name__=='__main__':unittest.main()
