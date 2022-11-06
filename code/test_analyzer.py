import CIPS_Analyzer

def test_debug():
    CIPS = CIPS_Analyzer.CIPS()
    start_status = CIPS.debugStatus()
    assert start_status == False
    CIPS.enableDebug()
    status = CIPS.debugStatus()
    assert status == True

def test_updateEndpoint():
    CIPS = CIPS_Analyzer.CIPS()
    response = CIPS.updateEndpointURL("test123")
    assert response == "test123"
    