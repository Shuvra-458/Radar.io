import asyncio
from app.nodes.redflag_scorer import redflag_scorer_node, DIMENSIONS
from app.state import Finding


async def main():
    findings = [Finding(
        task_id="salary_reliability",
        question="Are there reports of delayed salaries?",
        summary="Several Reddit threads describe salary delays of 30-45 days.",
        sources=["https://reddit.com/r/developersIndia/...", "https://reddit.com/r/india/..."],
    )]
    result = await redflag_scorer_node({
        "company": "TestCo", "mode": "employer", "findings": findings,
    })
    v = result["verdict"]
    present = set(v.dimensions.model_dump().keys())
    missing = [d for d in DIMENSIONS if d not in present]
    assert not missing, f"missing dimensions: {missing}"
    print(f"OK: verdict={v.verdict} score={v.overall_score}")
    for name in DIMENSIONS:
        d = getattr(v.dimensions, name)
        print(f"  {name}: {d.score}/10 [{d.confidence}]")


if __name__ == "__main__":
    asyncio.run(main())