from app.services.document_processor import DocumentProcessor


def test_attention_paper_title_ignores_permission_preamble():
    text = (
        "Providedproperattributionisprovided,Googleherebygrantspermissionto "
        "reproducethetablesandfiguresinthispapersolelyforuseinjournalisticor "
        "scholarlyworks. Attention Is All You Need AshishVaswani* "
        "NoamShazeer* GoogleBrain"
    )

    assert DocumentProcessor().extract_title_from_text(text) == "Attention Is All You Need"
