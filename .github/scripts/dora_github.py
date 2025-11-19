import os, sys, csv, json, time
from datetime import datetime, timedelta, timezone
from dateutil.parser import isoparse
import requests

# --- Config ---
OWNER = os.getenv("OWNER")
REPO = os.getenv("REPO")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
WINDOW_DAYS = int(os.getenv("WINDOW_DAYS", "30"))
TOKEN = os.getenv("GITHUB_TOKEN")

if not (OWNER and REPO and TOKEN):
    print("Faltan OWNER/REPO/GITHUB_TOKEN en el entorno.", file=sys.stderr)
    sys.exit(1)

BASE = f"https://api.github.com"
HDRS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"}

since_dt = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
since_iso = since_dt.isoformat()

# --- Helpers de paginación ---
def gh_get(url, params=None):
    out = []
    page = 1
    while True:
        p = params.copy() if params else {}
        p["per_page"] = 100
        p["page"] = page
        r = requests.get(url, headers=HDRS, params=p)
        if r.status_code != 200:
            raise RuntimeError(f"GET {url} {r.status_code} {r.text}")
        data = r.json()
        if not isinstance(data, list):
            # endpoints que no son listas
            return data
        out.extend(data)
        if "next" not in r.links:
            break
        page += 1
    return out

# --- 1) Deployments a production (success/failure) ---
deploys = gh_get(f"{BASE}/repos/{OWNER}/{REPO}/deployments",
                 params={"environment": ENVIRONMENT})
# Filtrar ventana
deploys = [d for d in deploys if isoparse(d["created_at"]) >= since_dt]

# Obtener statuses por deployment
def get_deploy_status(deployment_id):
    url = f"{BASE}/repos/{OWNER}/{REPO}/deployments/{deployment_id}/statuses"
    st = gh_get(url)
    # Tomar el último status como "estado final"
    return st[-1] if st else None

deploy_rows = []
for d in deploys:
    st = get_deploy_status(d["id"])
    final_state = st["state"] if st else "unknown"
    final_time = isoparse(st["created_at"]) if st else isoparse(d["created_at"])
    deploy_rows.append({
        "id": d["id"],
        "sha": d.get("sha"),
        "created_at": isoparse(d["created_at"]),
        "final_state": final_state,             # success | failure | inactive | error | pending...
        "final_time": final_time
    })

# Orden por tiempo final (cronológico)
deploy_rows.sort(key=lambda x: x["final_time"])

# --- 2) PRs merged a main (ventana) ---
# Usamos el Search API para PRs merged recientes
q = f"repo:{OWNER}/{REPO} is:pr is:merged base:main merged:>={since_dt.date().isoformat()}"
prs_search_url = f"{BASE}/search/issues"
prs_resp = requests.get(prs_search_url, headers=HDRS, params={"q": q, "per_page": 100})
if prs_resp.status_code != 200:
    raise RuntimeError(f"Search PRs {prs_resp.status_code} {prs_resp.text}")
prs_items = prs_resp.json().get("items", [])

# Para cada PR, pedimos detalles para obtener merge_commit_sha
def get_pr(num):
    url = f"{BASE}/repos/{OWNER}/{REPO}/pulls/{num}"
    r = requests.get(url, headers=HDRS)
    if r.status_code != 200:
        raise RuntimeError(f"PR {num} {r.status_code} {r.text}")
    return r.json()

pr_data = []
for it in prs_items:
    number = it["number"]
    pr = get_pr(number)
    merged_at = isoparse(pr["merged_at"]) if pr["merged_at"] else None
    if not merged_at or merged_at < since_dt:
        continue
    pr_data.append({
        "number": number,
        "merged_at": merged_at,
        "merge_commit_sha": pr.get("merge_commit_sha"),
        "title": pr.get("title","")
    })

# Orden por merged_at
pr_data.sort(key=lambda x: x["merged_at"])

# --- Mapear PRs a deployments (aprox): PRs entre success(k-1) y success(k) pertenecen al success(k) ---
success_deploys = [d for d in deploy_rows if d["final_state"] == "success"]
failure_deploys = [d for d in deploy_rows if d["final_state"] == "failure"]

# Ventanas entre despliegues success consecutivos
windows = []
prev_success_time = None
for sd in success_deploys:
    cur = sd["final_time"]
    windows.append((prev_success_time, cur, sd))
    prev_success_time = cur

# Asignar PRs a cada ventana
deploy_to_prs = {sd["id"]: [] for sd in success_deploys}
for (prev_t, cur_t, sd) in windows:
    for pr in pr_data:
        if pr["merged_at"] <= cur_t and (prev_t is None or pr["merged_at"] > prev_t):
            deploy_to_prs[sd["id"]].append(pr)

# --- Lead Time por PR (merged_at → deploy_success.final_time) ---
lead_times_hours = []
per_pr_rows = []
for sd in success_deploys:
    dep_time = sd["final_time"]
    prs = deploy_to_prs.get(sd["id"], [])
    for pr in prs:
        lt = (dep_time - pr["merged_at"]).total_seconds() / 3600.0
        lead_times_hours.append(lt)
        per_pr_rows.append({
            "deployment_id": sd["id"],
            "deployment_time": dep_time.isoformat(),
            "pr_number": pr["number"],
            "pr_title": pr["title"],
            "merged_at": pr["merged_at"].isoformat(),
            "lead_time_hours": round(lt, 3)
        })

# --- Deployment Frequency (success por día) ---
# Conteo simple por fecha (UTC)
from collections import Counter, defaultdict
df_counter = Counter(sd["final_time"].date().isoformat() for sd in success_deploys)
deployment_frequency_total = sum(df_counter.values())
deployment_frequency_per_day = deployment_frequency_total / max(1, WINDOW_DAYS)

# --- MTTR: para cada failure, tiempo hasta el siguiente success ---
mttr_list = []
succ_times = [sd["final_time"] for sd in success_deploys]
succ_times.sort()
for fd in failure_deploys:
    fail_t = fd["final_time"]
    # siguiente success posterior a fail_t
    next_succ = next((t for t in succ_times if t > fail_t), None)
    if next_succ:
        mttr_list.append((next_succ - fail_t).total_seconds() / 3600.0)

mttr_hours = sum(mttr_list)/len(mttr_list) if mttr_list else None

# --- CFR ---
total_deploys = len(success_deploys) + len(failure_deploys)
cfr = (len(failure_deploys)/total_deploys*100.0) if total_deploys > 0 else None

# --- Agregados Lead Time ---
def pct(values, p):
    if not values: return None
    s = sorted(values)
    k = int(round((p/100.0)*(len(s)-1)))
    return s[k]

lead_p50 = pct(lead_times_hours, 50) if lead_times_hours else None
lead_p85 = pct(lead_times_hours, 85) if lead_times_hours else None
lead_p95 = pct(lead_times_hours, 95) if lead_times_hours else None

# --- Salidas ---
summary = {
    "repo": f"{OWNER}/{REPO}",
    "environment": ENVIRONMENT,
    "window_days": WINDOW_DAYS,
    "since": since_iso,
    "deploy_success": len(success_deploys),
    "deploy_failure": len(failure_deploys),
    "deployment_frequency_total": deployment_frequency_total,
    "deployment_frequency_per_day": round(deployment_frequency_per_day, 3),
    "lead_time_hours_p50": round(lead_p50, 3) if lead_p50 is not None else None,
    "lead_time_hours_p85": round(lead_p85, 3) if lead_p85 is not None else None,
    "lead_time_hours_p95": round(lead_p95, 3) if lead_p95 is not None else None,
    "mttr_hours_mean": round(mttr_hours, 3) if mttr_hours is not None else None,
    "cfr_percent": round(cfr, 2) if cfr is not None else None
}

with open("dora_latest.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)

# CSV por día (DF) + agregados
with open("dora_metrics.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["metric","key","value"])
    for day, cnt in sorted(df_counter.items()):
        w.writerow(["deployment_frequency_day", day, cnt])
    for k, v in summary.items():
        if k not in ("repo","environment","since"):
            w.writerow(["summary", k, v])

# Tabla Markdown para el Job Summary
def fmt(v): return ("—" if v is None else v)
with open("dora_table.md", "w") as f:
    f.write("| Métrica | Valor |\n|---|---:|\n")
    f.write(f"| Repo | `{summary['repo']}` |\n")
    f.write(f"| Environment | `{summary['environment']}` |\n")
    f.write(f"| Ventana (días) | {summary['window_days']} |\n")
    f.write(f"| Deploys (success) | {summary['deploy_success']} |\n")
    f.write(f"| Deploys (failure) | {summary['deploy_failure']} |\n")
    f.write(f"| Deployment Frequency total | {summary['deployment_frequency_total']} |\n")
    f.write(f"| Deployment Frequency / día | {summary['deployment_frequency_per_day']} |\n")
    f.write(f"| Lead Time p50 (h) | {fmt(summary['lead_time_hours_p50'])} |\n")
    f.write(f"| Lead Time p85 (h) | {fmt(summary['lead_time_hours_p85'])} |\n")
    f.write(f"| Lead Time p95 (h) | {fmt(summary['lead_time_hours_p95'])} |\n")
    f.write(f"| MTTR (h) | {fmt(summary['mttr_hours_mean'])} |\n")
    f.write(f"| CFR (%) | {fmt(summary['cfr_percent'])} |\n")

# Extra: CSV por PR con lead time
with open("dora_pr_lead_times.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["deployment_id","deployment_time","pr_number","pr_title","merged_at","lead_time_hours"])
    w.writeheader()
    for row in per_pr_rows:
        w.writerow(row)

print(json.dumps(summary, indent=2, default=str))
