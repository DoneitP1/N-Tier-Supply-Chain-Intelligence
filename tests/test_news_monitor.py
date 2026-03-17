import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from services.news_monitor import get_real_news, poll_news_and_analyze
from models.schemas import NewsRiskData, EventClassification, ImpactDetails

@pytest.mark.asyncio
async def test_get_real_news_success():
    mock_feed = MagicMock()
    mock_entry = MagicMock()
    mock_entry.title = "Supply Chain Strike"
    mock_feed.entries = [mock_entry]
    
    with patch("feedparser.parse", return_value=mock_feed):
        news = await get_real_news()
        assert len(news) == 1
        assert news[0] == "Supply Chain Strike"

@pytest.mark.asyncio
async def test_poll_news_and_analyze_critical_hit(mock_db_connection):
    # Mock news list
    news_titles = ["Flash flood hits electronics factory"]
    
    # Mock critical risk extraction
    extracted = NewsRiskData(
        event_classification=EventClassification(
            is_supply_chain_risk=True, 
            event_type="Natural Disaster", 
            severity="Critical", 
            confidence_score=0.95
        ),
        impact_details=ImpactDetails(
            locations_affected=["Seoul"], 
            entities_affected=["Samsung"], 
            confidence_score=0.9
        ),
        summary="Critical flood in Seoul",
        overall_assessment_confidence=0.9
    )
    
    with patch("services.news_monitor.get_real_news", return_value=news_titles):
        with patch("services.news_monitor.extract_news_risk_via_llm", return_value=extracted):
            with patch("services.news_monitor.resolve_supplier_name", side_effect=lambda x: x):
                await poll_news_and_analyze()
                
                # Check if Neo4j was hit for critical risk
                assert mock_db_connection.execute_query.called
                args, _ = mock_db_connection.execute_query.call_args
                params = args[1]
                assert params["severity"] == "Critical"

@pytest.mark.asyncio
async def test_poll_news_and_analyze_low_risk_ignored(mock_db_connection):
    news_titles = ["Minor logistics delay"]
    
    # Mock low risk
    extracted = NewsRiskData(
        event_classification=EventClassification(
            is_supply_chain_risk=True, 
            event_type="Delay", 
            severity="Low", 
            confidence_score=0.8
        ),
        impact_details=ImpactDetails(locations_affected=[], entities_affected=[], confidence_score=0.8),
        summary="Minor delay",
        overall_assessment_confidence=0.8
    )
    
    mock_db_connection.execute_query.reset_mock()
    
    with patch("services.news_monitor.get_real_news", return_value=news_titles):
        with patch("services.news_monitor.extract_news_risk_via_llm", return_value=extracted):
            await poll_news_and_analyze()
            
            # Neo4j should NOT be hit for Low risk
            assert not mock_db_connection.execute_query.called
