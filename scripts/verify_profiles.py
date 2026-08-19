import sys
sys.path.insert(0, ".")
from app.services.aggregation_service import get_member_360_profile

for mid in ['M00001', 'M00002', 'M00003', 'M00004', 'M00005']:
    p = get_member_360_profile(mid)
    m = p['member']
    s = p['stats']
    print(f"{mid}: {m['first_name']} {m['last_name']} | Phone: {m['phone']} | Email: {m['email']} | PIN: {m['postal_code']}")
    print(f"   Total Expenses: Rs. {s['total_claim_amount']:,.2f} | Plan Paid: Rs. {s['plan_coverage_paid']:,.2f} | Copay: Rs. {s['member_responsibility']:,.2f} | Claims: {s['claims_count']}")
    print(f"   Medications: {s['medications_count']} | Care Gaps: {s['care_gaps_count']} | Auths: {s['authorizations_count']} | Requests: {s['requests_count']}")
    print()
