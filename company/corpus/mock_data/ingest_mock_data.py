"""
ingest_mock_data.py — run once before demo
python ingest_mock_data.py
"""

import os, glob
import chromadb
from chromadb.utils import embedding_functions

DATA_DIR    = "./mock_data"
CHROMA_PATH = "./chroma_db"

embedding_fn = embedding_functions.OllamaEmbeddingFunction(
    url="http://localhost:11434/api/embeddings",
    model_name="nomic-embed-text",
)

FILE_METADATA = {
    # ARC 1 — Rate Limiting
    "API_Outage_Export_Endpoint_2023.md":         {"author":"Marcus Chen","year":2023,"outcome":"P0 outage — $94K ARR churned","risk_level":"Critical","department":"Engineering","project":"API Infrastructure","doc_type":"Incident Report","arc":"rate_limiting","tags":"API,outage,rate limiting,endpoint,database,connection pool,export,P0"},
    "Export_Endpoint_Outage_Postmortem_2023.md":  {"author":"Priya Patel","year":2023,"outcome":"3 enterprise customers churned $94K ARR","risk_level":"Critical","department":"Engineering","project":"API Infrastructure","doc_type":"Postmortem","arc":"rate_limiting","tags":"postmortem,API,rate limiting,outage,pre-ship checklist,Marcus Chen"},
    "Rate_Limiting_Middleware_Docs.md":           {"author":"Marcus Chen","year":2023,"outcome":"Adopted — zero repeat outages","risk_level":"High","department":"Engineering","project":"API Infrastructure","doc_type":"Engineering Docs","arc":"rate_limiting","tags":"rate limiting,middleware,@rateLimit,API,endpoint,pre-ship checklist"},
    "API_Endpoint_PreShip_Checklist.md":          {"author":"Marcus Chen","year":2023,"outcome":"Adopted — mandatory before merge","risk_level":"High","department":"Engineering","project":"API Infrastructure","doc_type":"Checklist","arc":"rate_limiting","tags":"checklist,endpoint,rate limiting,pagination,load test,pre-ship"},
    # ARC 2 — Cloud Cost
    "AWS_Bill_GPU_Instances_2022.md":             {"author":"Marcus Chen","year":2022,"outcome":"$31,200 unplanned AWS spend","risk_level":"Critical","department":"Engineering","project":"Cloud Infrastructure","doc_type":"Incident Report","arc":"cloud_cost","tags":"AWS,GPU,cost,billing,p3.8xlarge,instances,experiment,Jake Morrison"},
    "Cloud_Cost_Policy.md":                       {"author":"Priya Patel","year":2022,"outcome":"Adopted — zero surprise bills since","risk_level":"High","department":"Engineering","project":"Cloud Infrastructure","doc_type":"Policy","arc":"cloud_cost","tags":"AWS,cost,billing alerts,GPU,instances,tagging,auto-shutdown,policy"},
    # ARC 3 — Enterprise Deals
    "Helix_Enterprise_Deal_Postmortem_2024.md":   {"author":"Priya Patel","year":2024,"outcome":"Customer churned, engineer resigned, net -$130K","risk_level":"Critical","department":"Sales / Engineering","project":"Helix Capital","doc_type":"Postmortem","arc":"enterprise_deals","tags":"enterprise,deal,scope,SSO,integration,white-label,burnout,overrun,Sarah Kim"},
    "Enterprise_Deal_Process.md":                 {"author":"Jake Morrison","year":2024,"outcome":"Adopted — 3 subsequent deals on time","risk_level":"High","department":"Sales / Engineering","project":"Sales Process","doc_type":"Policy","arc":"enterprise_deals","tags":"enterprise,deal,scope,technical review,SSO,integration,change order,pre-close"},
    # ARC 4 — Vendor Lock-in
    "Mapbox_Pricing_Crisis_2023.md":              {"author":"Marcus Chen","year":2023,"outcome":"12x price hike, emergency 6-week migration","risk_level":"Critical","department":"Engineering","project":"Mapping Feature","doc_type":"Incident Report","arc":"vendor_lock","tags":"vendor,pricing,Mapbox,API,dependency,lock-in,migration,unit economics"},
    "Third_Party_Dependency_Policy.md":           {"author":"Priya Patel","year":2023,"outcome":"Adopted — abstraction layer now standard","risk_level":"High","department":"Engineering","project":"Engineering Standards","doc_type":"Policy","arc":"vendor_lock","tags":"vendor,dependency,abstraction,pricing,lock-in,fallback,third-party,API"},
    # ARC 5 — Secrets / Security
    "GitHub_Credentials_Leak_2023.md":            {"author":"Marcus Chen","year":2023,"outcome":"$3,200 net cost, production DB connection string exposed","risk_level":"Critical","department":"Engineering","project":"Security","doc_type":"Incident Report","arc":"secrets","tags":"security,credentials,env,AWS,GitHub,leak,crypto mining,Stripe,Postgres,production"},
    "Secrets_Management_Policy.md":               {"author":"Marcus Chen","year":2023,"outcome":"Adopted — no credential leaks since","risk_level":"Critical","department":"Engineering","project":"Security","doc_type":"Policy","arc":"secrets","tags":"secrets,credentials,.env,git-secrets,1Password,policy,GitHub,pre-commit"},
    # ARC 6 — DB Migration
    "Database_Migration_Failure_2022.md":         {"author":"Marcus Chen","year":2022,"outcome":"3h40m data loss, 6 customers churned, $47K ARR","risk_level":"Critical","department":"Engineering","project":"Database Infrastructure","doc_type":"Incident Report","arc":"db_migration","tags":"database,migration,data loss,Postgres,rollback,snapshot,production,RDS"},
    "Database_Migration_Runbook.md":              {"author":"Marcus Chen","year":2022,"outcome":"Adopted — no migration failures since","risk_level":"High","department":"Engineering","project":"Database Infrastructure","doc_type":"Runbook","arc":"db_migration","tags":"database,migration,runbook,snapshot,rollback,RDS,checklist,Postgres"},
    # ARC 7 — Feature Flags
    "Billing_UI_NoFlag_Incident_2024.md":         {"author":"Jake Morrison","year":2024,"outcome":"34% error rate, 2h12m rollback","risk_level":"High","department":"Engineering / Product","project":"Billing UI","doc_type":"Incident Report","arc":"feature_flags","tags":"feature flag,billing,UI,rollout,canary,rollback,error rate,annual plan"},
    "Feature_Flag_Policy.md":                     {"author":"Jake Morrison","year":2024,"outcome":"Adopted — LaunchDarkly mandatory","risk_level":"High","department":"Engineering / Product","project":"Release Process","doc_type":"Policy","arc":"feature_flags","tags":"feature flag,LaunchDarkly,canary,rollout,billing,auth,checkout,release"},
    # ARC 8 — Hiring
    "Hiring_Ahead_Of_Revenue_Retro_2023.md":      {"author":"Priya Patel","year":2023,"outcome":"2 layoffs, team trust damaged, 5 months runway recovered","risk_level":"Critical","department":"Leadership","project":"Headcount Planning","doc_type":"Retrospective","arc":"hiring","tags":"hiring,layoffs,runway,Series A,headcount,burn rate,revenue,people"},
    "Hiring_Policy.md":                           {"author":"Priya Patel","year":2023,"outcome":"Adopted — no repeat over-hiring","risk_level":"High","department":"Leadership","project":"Headcount Planning","doc_type":"Policy","arc":"hiring","tags":"hiring,policy,runway,revenue trigger,headcount,burn rate,Series A,funding"},
    # SUPPORTING
    "Engineering_Retro_Q1_2024.md":               {"author":"Priya Patel","year":2024,"outcome":"Process changes confirmed embedded","risk_level":"Medium","department":"Engineering","project":"Process Review","doc_type":"Meeting Notes","arc":"general","tags":"retro,lessons,rate limiting,AWS,enterprise,process"},
    "OnCall_Burnout_Restructure_2024.md":          {"author":"Priya Patel","year":2024,"outcome":"On-call rotation restructured","risk_level":"High","department":"Engineering","project":"On-Call","doc_type":"Postmortem","arc":"people","tags":"on-call,burnout,PagerDuty,rotation,Marcus Chen,single point of failure"},
    "HackerNews_Launch_Failure_2023.md":           {"author":"Jake Morrison","year":2023,"outcome":"Site down during HN front page — 15% of signups captured","risk_level":"High","department":"Engineering / Product","project":"Growth","doc_type":"Retrospective","arc":"scalability","tags":"HackerNews,launch,traffic spike,auto-scaling,CDN,503,load test"},
    "Company_Lessons_Learned.md":                  {"author":"Priya Patel","year":2024,"outcome":"Onboarding reference","risk_level":"Low","department":"All","project":"Onboarding","doc_type":"Onboarding Doc","arc":"general","tags":"onboarding,lessons,institutional memory,new hire"},
    # NOISE
    "Dark_Mode_Discussion_Noise.md":              {"author":"Jake Morrison","year":2025,"outcome":"N/A","risk_level":"Low","department":"Product","project":"Roadmap","doc_type":"Slack Thread","arc":"noise","tags":"dark mode,UI,feature,backlog"},
    "Offsite_Planning_Noise_Thread.md":           {"author":"Jake Morrison","year":2025,"outcome":"N/A","risk_level":"Low","department":"General","project":"Offsite","doc_type":"Slack Thread","arc":"noise","tags":"offsite,planning"},
    "Safari_Datepicker_Bug_Noise_Thread.md":      {"author":"Alex Rivera","year":2025,"outcome":"N/A","risk_level":"Low","department":"Engineering","project":"Bug Fix","doc_type":"Slack Thread","arc":"noise","tags":"safari,bug,datepicker"},
    "Standup_2025_01_20.md":                      {"author":"Priya Patel","year":2025,"outcome":"N/A","risk_level":"Low","department":"Engineering","project":"Standup","doc_type":"Meeting Notes","arc":"noise","tags":"standup"},
    "Weekly_Eng_Sync_2025_01_28.md":              {"author":"Jake Morrison","year":2025,"outcome":"N/A","risk_level":"Low","department":"Engineering","project":"Weekly Sync","doc_type":"Meeting Notes","arc":"noise","tags":"weekly sync"},
}

def chunk_document(text: str, chunk_size: int = 600) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) < chunk_size:
            current += "\n\n" + para
        else:
            if current:
                chunks.append(current.strip())
            current = para
    if current:
        chunks.append(current.strip())
    return chunks

def ingest_all():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(
        name="organizational_memory",
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )
    all_md = glob.glob(f"{DATA_DIR}/**/*.md", recursive=True)
    print(f"\n🧠 Ingesting {len(all_md)} documents...\n")
    arc_counts: dict[str, int] = {}
    total_chunks = 0
    for filepath in all_md:
        filename = os.path.basename(filepath)
        meta = FILE_METADATA.get(filename, {"author":"Unknown","year":2024,"outcome":"Unknown","risk_level":"Low","department":"General","project":"General","doc_type":"Document","arc":"general","tags":""})
        arc = meta.get("arc","general")
        arc_counts[arc] = arc_counts.get(arc,0) + 1
        with open(filepath,"r") as f:
            text = f.read()
        chunks = chunk_document(text)
        icon = "🔇" if arc == "noise" else "✅"
        print(f"  {icon} [{arc:<16}] {filename}  ({len(chunks)} chunks)")
        for i, chunk in enumerate(chunks):
            collection.upsert(
                ids=[f"{filename.replace('.md','').replace(' ','_')}__chunk_{i}"],
                documents=[chunk],
                metadatas=[{**meta, "source_file": filename, "chunk_index": i}],
            )
            total_chunks += 1
    print(f"\n{'─'*60}")
    print(f"  Files: {len(all_md)}   Chunks: {total_chunks}")
    print(f"  ChromaDB: {CHROMA_PATH}\n")
    print(f"  Arcs:")
    for arc, n in sorted(arc_counts.items()):
        print(f"    {arc:<22} {n} files")
    print(f"\n  ▶  python main.py\n")

if __name__ == "__main__":
    ingest_all()
