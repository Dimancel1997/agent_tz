#!/usr/bin/env python3
"""
Unit tests for Telegram Agent Bot MCP Tools
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime

# Import the modules to test
from tools import MCPTools, create_calendar_event, send_email_notification, search_web


class TestMCPTools:
    """Test cases for MCP Tools"""
    
    @pytest.fixture
    def mcp_tools(self):
        """Create MCPTools instance for testing"""
        with patch('tools.build') as mock_build:
            tools = MCPTools()
            tools.calendar_service = Mock()
            tools.gmail_service = Mock()
            return tools
    
    @pytest.mark.asyncio
    async def test_create_event_success(self, mcp_tools):
        """Test successful calendar event creation"""
        # Mock calendar service response
        mock_event = {
            'id': 'test_event_123',
            'htmlLink': 'https://calendar.google.com/event/test'
        }
        mcp_tools.calendar_service.events().insert().execute.return_value = mock_event
        
        # Test event creation
        result = await mcp_tools.create_event("Test Meeting", "10.10.2025")
        
        assert result['success'] is True
        assert result['event_id'] == 'test_event_123'
        assert result['summary'] == "Test Meeting"
        assert 'link' in result
    
    @pytest.mark.asyncio
    async def test_create_event_invalid_date(self, mcp_tools):
        """Test calendar event creation with invalid date"""
        result = await mcp_tools.create_event("Test Meeting", "invalid_date")
        
        assert result['success'] is False
        assert 'error' in result
        assert 'Invalid date format' in result['error']
    
    @pytest.mark.asyncio
    async def test_create_event_api_error(self, mcp_tools):
        """Test calendar event creation with API error"""
        from googleapiclient.errors import HttpError
        
        # Mock API error
        error = HttpError(Mock(), b'{"error": "API Error"}')
        mcp_tools.calendar_service.events().insert().execute.side_effect = error
        
        result = await mcp_tools.create_event("Test Meeting", "10.10.2025")
        
        assert result['success'] is False
        assert 'Calendar API error' in result['error']
    
    @pytest.mark.asyncio
    async def test_send_email_success(self, mcp_tools):
        """Test successful email sending"""
        # Mock Gmail service response
        mock_message = {'id': 'test_message_123'}
        mcp_tools.gmail_service.users().messages().send().execute.return_value = mock_message
        
        # Test email sending
        result = await mcp_tools.send_email("test@example.com", "Test Subject", "Test Body")
        
        assert result['success'] is True
        assert result['message_id'] == 'test_message_123'
        assert result['to'] == "test@example.com"
        assert result['subject'] == "Test Subject"
    
    @pytest.mark.asyncio
    async def test_send_email_api_error(self, mcp_tools):
        """Test email sending with API error"""
        from googleapiclient.errors import HttpError
        
        # Mock API error
        error = HttpError(Mock(), b'{"error": "API Error"}')
        mcp_tools.gmail_service.users().messages().send().execute.side_effect = error
        
        result = await mcp_tools.send_email("test@example.com", "Test Subject", "Test Body")
        
        assert result['success'] is False
        assert 'Gmail API error' in result['error']
    
    @pytest.mark.asyncio
    async def test_web_search_success(self, mcp_tools):
        """Test successful web search"""
        # Mock DuckDuckGo API response
        mock_response = {
            'Abstract': 'Test abstract text',
            'Heading': 'Test Heading',
            'AbstractURL': 'https://example.com',
            'RelatedTopics': [
                {
                    'Text': 'Related topic text',
                    'FirstURL': 'https://related.com'
                }
            ]
        }
        
        with patch('tools.requests.get') as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status.return_value = None
            
            result = await mcp_tools.web_search("test query")
            
            assert result['success'] is True
            assert result['query'] == "test query"
            assert len(result['results']) > 0
            assert result['results'][0]['type'] == 'abstract'
    
    @pytest.mark.asyncio
    async def test_web_search_request_error(self, mcp_tools):
        """Test web search with request error"""
        import requests
        
        with patch('tools.requests.get') as mock_get:
            mock_get.side_effect = requests.RequestException("Network error")
            
            result = await mcp_tools.web_search("test query")
            
            assert result['success'] is False
            assert 'Search request failed' in result['error']
    
    def test_parse_date_formats(self, mcp_tools):
        """Test date parsing with different formats"""
        # Test DD.MM.YYYY format
        date = mcp_tools._parse_date("10.10.2025")
        assert date is not None
        assert date.year == 2025
        assert date.month == 10
        assert date.day == 10
        
        # Test relative dates
        today = mcp_tools._parse_date("сегодня")
        assert today is not None
        
        tomorrow = mcp_tools._parse_date("завтра")
        assert tomorrow is not None
        
        # Test invalid date
        invalid = mcp_tools._parse_date("invalid")
        assert invalid is None
    
    @pytest.mark.asyncio
    async def test_calendar_health_check(self, mcp_tools):
        """Test calendar health check"""
        # Mock successful health check
        mock_calendar_list = {'items': [{'id': 'primary'}, {'id': 'work'}]}
        mcp_tools.calendar_service.calendarList().list().execute.return_value = mock_calendar_list
        
        result = await mcp_tools.check_calendar_health()
        
        assert result['status'] == 'healthy'
        assert result['calendars_count'] == 2
        assert result['service'] == 'Google Calendar'
    
    @pytest.mark.asyncio
    async def test_gmail_health_check(self, mcp_tools):
        """Test Gmail health check"""
        # Mock successful health check
        mock_profile = {
            'emailAddress': 'test@gmail.com',
            'messagesTotal': 1000
        }
        mcp_tools.gmail_service.users().getProfile().execute.return_value = mock_profile
        
        result = await mcp_tools.check_gmail_health()
        
        assert result['status'] == 'healthy'
        assert result['email'] == 'test@gmail.com'
        assert result['messages_total'] == 1000
        assert result['service'] == 'Gmail'
    
    @pytest.mark.asyncio
    async def test_search_health_check(self, mcp_tools):
        """Test search health check"""
        # Mock successful search
        with patch.object(mcp_tools, 'web_search') as mock_search:
            mock_search.return_value = {
                'success': True,
                'results': [{'title': 'Test', 'snippet': 'Test snippet'}]
            }
            
            result = await mcp_tools.check_search_health()
            
            assert result['status'] == 'healthy'
            assert result['service'] == 'DuckDuckGo Search'
            assert result['test_results'] == 1


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    @pytest.mark.asyncio
    async def test_create_calendar_event_function(self):
        """Test create_calendar_event convenience function"""
        with patch('tools.mcp_tools.create_event') as mock_create:
            mock_create.return_value = {'success': True, 'event_id': 'test'}
            
            result = await create_calendar_event("Test", "10.10.2025")
            
            assert result['success'] is True
            mock_create.assert_called_once_with("Test", "10.10.2025")
    
    @pytest.mark.asyncio
    async def test_send_email_notification_function(self):
        """Test send_email_notification convenience function"""
        with patch('tools.mcp_tools.send_email') as mock_send:
            mock_send.return_value = {'success': True, 'message_id': 'test'}
            
            result = await send_email_notification("test@example.com", "Subject", "Body")
            
            assert result['success'] is True
            mock_send.assert_called_once_with("test@example.com", "Subject", "Body")
    
    @pytest.mark.asyncio
    async def test_search_web_function(self):
        """Test search_web convenience function"""
        with patch('tools.mcp_tools.web_search') as mock_search:
            mock_search.return_value = {'success': True, 'results': []}
            
            result = await search_web("test query")
            
            assert result['success'] is True
            mock_search.assert_called_once_with("test query", 3)


class TestIntegration:
    """Integration tests"""
    
    @pytest.mark.asyncio
    async def test_all_mcp_health_check(self):
        """Test checking health of all MCP tools"""
        with patch('tools.check_all_mcp_health') as mock_health:
            mock_health.return_value = {
                'calendar': {'status': 'healthy'},
                'gmail': {'status': 'healthy'},
                'search': {'status': 'healthy'}
            }
            
            from tools import check_all_mcp_health
            result = await check_all_mcp_health()
            
            assert 'calendar' in result
            assert 'gmail' in result
            assert 'search' in result


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
