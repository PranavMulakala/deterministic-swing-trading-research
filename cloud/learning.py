"""Evidence-based review agent. No LLM, code edits, promotions, or order capability."""
import hashlib
import json

def review(orb, lite, policy, completed_days, source_digest):
    minimum=policy['review']
    if minimum['promotion']!='disabled' or minimum['risk_edits']!='forbidden':
        raise ValueError('Learning policy cannot authorize promotion or risk edits')
    evidence={'completed_sessions':len(completed_days), 'source_digest':source_digest,
              'last_evidence_day':max(completed_days) if completed_days else None}
    findings=[]
    proposals=[]
    for label,run in sorted(orb.items()):
        if not run.get('complete'):
            findings.append({'kind':'unresolved_execution','scenario':label,'evidence':run.get('unresolved')})
        elif not run.get('trades'):
            findings.append({'kind':'no_closed_trades_not_proof_of_edge','scenario':label})
    pairs=[]
    for delay in policy['orb']['delay_seconds']:
        for cost in policy['orb']['cost_bps']:
            a=orb.get(f'{delay}s_{cost}bps_A')
            b=orb.get(f'{delay}s_{cost}bps_B')
            if not a or not b or not a['complete'] or not b['complete']:
                pairs.append({'delay':delay,'cost':cost,'status':'blocked_incomplete'})
                continue
            enough=(len(completed_days)>=minimum['minimum_sessions'] and
                    min(len(a['trades']),len(b['trades']))>=minimum['minimum_closed_trades_per_arm'])
            difference=float(b['net_return'])-float(a['net_return'])
            pairs.append({'delay':delay,'cost':cost,'status':'eligible_for_statistical_review_not_promotion' if enough else 'insufficient_evidence',
                          'B_minus_A_net_return':difference,'trades_A':len(a['trades']),'trades_B':len(b['trades'])})
    # A review request, never an automatic strategy change. No score rewards simply adding trades.
    if any(p['status']=='eligible_for_statistical_review_not_promotion' for p in pairs):
        candidate={'type':'evaluate_existing_RVOL_arm_against_unfiltered_control',
                   'status':'proposed_not_approved', 'evidence':evidence,
                   'change':'No deployed rule changes; investigate the existing A/B contrast',
                   'required_test':'Freeze a new future interval before testing; paired uncertainty, both cost scenarios, and concentration checks',
                   'effective_after':evidence['last_evidence_day'], 'auto_promote':False}
        candidate['id']=hashlib.sha256(json.dumps(candidate,sort_keys=True).encode()).hexdigest()[:20]
        proposals.append(candidate)
    return {'agent_type':'deterministic_evidence_reviewer_not_self_training_LLM',
            'status':'review_proposed' if proposals else 'collecting_evidence_no_improvement_claim',
            'evidence':evidence,'paired_comparisons':pairs,'findings':findings,'proposals':proposals,
            'lite_scenarios':len(lite),'promotion_enabled':False,
            'risk_rules_changed':False,'training_or_inference_cost_usd':0}
