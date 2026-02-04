@router.get("/report")
async def get_report():
    discovery_data = discovery_engine.latest_results
    return {"report": discovery_data.get("report", "No report generated yet")}
