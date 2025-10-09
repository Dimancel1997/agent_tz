#!/usr/bin/env python3
"""
MCP Tools module for Telegram Agent Bot
Implements Google Calendar, Gmail, and Web Search functionality
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import re

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    import requests
except ImportError as e:
    logging.error(f"Required packages not installed: {e}")
    raise

logger = logging.getLogger(__name__)

# Google API Scopes
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.send'
]

class MCPTools:
    """MCP (Model Context Protocol) Tools for Calendar, Gmail, and Web Search"""
    
    def __init__(self):
        self.calendar_service = None
        self.gmail_service = None
        self.credentials = None
        
        # Initialize Google services
        self._initialize_google_services()
    
    def _initialize_google_services(self):
        """Initialize Google Calendar and Gmail services"""
        try:
            # Check if credentials.json exists
            credentials_path = 'credentials.json'
            if not os.path.exists(credentials_path):
                logger.warning("credentials.json not found. Google services will be disabled.")
                return
            
            # Load credentials
            self.credentials = self._get_google_credentials()
            
            if self.credentials:
                # Initialize Calendar service
                self.calendar_service = build('calendar', 'v3', credentials=self.credentials)
                logger.info("Google Calendar service initialized")
                
                # Initialize Gmail service
                self.gmail_service = build('gmail', 'v1', credentials=self.credentials)
                logger.info("Gmail service initialized")
            else:
                logger.warning("Failed to get Google credentials")
                
        except Exception as e:
            logger.error(f"Error initializing Google services: {e}")
    
    def _get_google_credentials(self):
        """Get Google API credentials"""
        try:
            creds = None
            token_path = 'token.json'
            
            # Load existing token
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
            # If no valid credentials, request authorization
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', SCOPES)
                    creds = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            
            return creds
            
        except Exception as e:
            logger.error(f"Error getting Google credentials: {e}")
            return None
    
    # Google Calendar Methods
    async def create_event(self, summary: str, date_str: str) -> Dict[str, Any]:
        """
        Create a calendar event
        
        Args:
            summary: Event title/description
            date_str: Date string (e.g., "10.10.2025", "завтра", "сегодня")
            
        Returns:
            Dict with success status and event details
        """
        try:
            if not self.calendar_service:
                return {
                    'success': False,
                    'error': 'Google Calendar service not initialized'
                }
            
            # Parse date
            event_date = self._parse_date(date_str)
            if not event_date:
                return {
                    'success': False,
                    'error': f'Invalid date format: {date_str}'
                }
            
            # Create event
            event = {
                'summary': summary,
                'start': {
                    'dateTime': event_date.isoformat(),
                    'timeZone': 'Europe/Moscow',
                },
                'end': {
                    'dateTime': (event_date + timedelta(hours=1)).isoformat(),
                    'timeZone': 'Europe/Moscow',
                },
                'description': f'Created by Telegram Agent Bot on {datetime.now().strftime("%Y-%m-%d %H:%M")}'
            }
            
            # Insert event
            created_event = self.calendar_service.events().insert(
                calendarId='primary', body=event
            ).execute()
            
            logger.info(f"Created calendar event: {summary} on {event_date}")
            
            return {
                'success': True,
                'event_id': created_event['id'],
                'summary': summary,
                'date': event_date.strftime('%Y-%m-%d %H:%M'),
                'link': created_event.get('htmlLink', '')
            }
            
        except HttpError as e:
            logger.error(f"Google Calendar API error: {e}")
            return {
                'success': False,
                'error': f'Calendar API error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error creating calendar event: {e}")
            return {
                'success': False,
                'error': f'Error creating event: {str(e)}'
            }
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object"""
        try:
            date_str = date_str.lower().strip()
            
            # Handle relative dates
            if date_str in ['сегодня', 'today']:
                return datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
            elif date_str in ['завтра', 'tomorrow']:
                return (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            
            # Handle DD.MM.YYYY format
            if re.match(r'\d{1,2}\.\d{1,2}\.\d{4}', date_str):
                return datetime.strptime(date_str, '%d.%m.%Y').replace(hour=9, minute=0, second=0, microsecond=0)
            
            # Handle YYYY-MM-DD format
            if re.match(r'\d{4}-\d{1,2}-\d{1,2}', date_str):
                return datetime.strptime(date_str, '%Y-%m-%d').replace(hour=9, minute=0, second=0, microsecond=0)
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing date '{date_str}': {e}")
            return None
    
    # Gmail Methods
    async def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """
        Send email via Gmail
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
            
        Returns:
            Dict with success status and message details
        """
        try:
            if not self.gmail_service:
                return {
                    'success': False,
                    'error': 'Gmail service not initialized'
                }
            
            # Create email message
            message = self._create_email_message(to, subject, body)
            
            # Send email
            sent_message = self.gmail_service.users().messages().send(
                userId='me', body=message
            ).execute()
            
            logger.info(f"Sent email to {to}: {subject}")
            
            return {
                'success': True,
                'message_id': sent_message['id'],
                'to': to,
                'subject': subject,
                'timestamp': datetime.now().isoformat()
            }
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return {
                'success': False,
                'error': f'Gmail API error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {
                'success': False,
                'error': f'Error sending email: {str(e)}'
            }
    
    def _create_email_message(self, to: str, subject: str, body: str) -> Dict[str, str]:
        """Create email message for Gmail API"""
        import base64
        from email.mime.text import MIMEText
        
        message = MIMEText(body, 'plain', 'utf-8')
        message['to'] = to
        message['subject'] = subject
        message['from'] = 'Telegram Agent Bot'
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        return {'raw': raw_message}
    
    # Web Search Methods
    async def web_search(self, query: str, max_results: int = 3) -> Dict[str, Any]:
        """
        Search the web using DuckDuckGo API
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            Dict with search results
        """
        try:
            # DuckDuckGo Instant Answer API
            url = "https://api.duckduckgo.com/"
            params = {
                'q': query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract results
            results = []
            
            # Abstract (main answer)
            if data.get('Abstract'):
                results.append({
                    'title': data.get('Heading', 'Answer'),
                    'snippet': data.get('Abstract', ''),
                    'url': data.get('AbstractURL', ''),
                    'type': 'abstract'
                })
            
            # Related topics
            for topic in data.get('RelatedTopics', [])[:max_results-1]:
                if isinstance(topic, dict) and topic.get('Text'):
                    results.append({
                        'title': topic.get('FirstURL', '').split('/')[-1] if topic.get('FirstURL') else 'Related Topic',
                        'snippet': topic.get('Text', ''),
                        'url': topic.get('FirstURL', ''),
                        'type': 'related'
                    })
            
            # Limit results
            results = results[:max_results]
            
            logger.info(f"Web search for '{query}' returned {len(results)} results")
            
            return {
                'success': True,
                'query': query,
                'results': results,
                'total_results': len(results)
            }
            
        except requests.RequestException as e:
            logger.error(f"Web search request error: {e}")
            return {
                'success': False,
                'error': f'Search request failed: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error performing web search: {e}")
            return {
                'success': False,
                'error': f'Search error: {str(e)}'
            }
    
    # Health Check Methods
    async def check_calendar_health(self) -> Dict[str, Any]:
        """Check Google Calendar service health"""
        try:
            if not self.calendar_service:
                return {'status': 'disabled', 'error': 'Service not initialized'}
            
            # Try to list calendars
            calendar_list = self.calendar_service.calendarList().list().execute()
            
            return {
                'status': 'healthy',
                'calendars_count': len(calendar_list.get('items', [])),
                'service': 'Google Calendar'
            }
            
        except Exception as e:
            logger.error(f"Calendar health check failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'service': 'Google Calendar'
            }
    
    async def check_gmail_health(self) -> Dict[str, Any]:
        """Check Gmail service health"""
        try:
            if not self.gmail_service:
                return {'status': 'disabled', 'error': 'Service not initialized'}
            
            # Try to get profile
            profile = self.gmail_service.users().getProfile(userId='me').execute()
            
            return {
                'status': 'healthy',
                'email': profile.get('emailAddress', ''),
                'messages_total': profile.get('messagesTotal', 0),
                'service': 'Gmail'
            }
            
        except Exception as e:
            logger.error(f"Gmail health check failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'service': 'Gmail'
            }
    
    async def check_search_health(self) -> Dict[str, Any]:
        """Check Web Search service health"""
        try:
            # Test search with simple query
            result = await self.web_search("test", max_results=1)
            
            if result['success']:
                return {
                    'status': 'healthy',
                    'service': 'DuckDuckGo Search',
                    'test_results': len(result.get('results', []))
                }
            else:
                return {
                    'status': 'error',
                    'error': result.get('error', 'Unknown error'),
                    'service': 'DuckDuckGo Search'
                }
                
        except Exception as e:
            logger.error(f"Search health check failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'service': 'DuckDuckGo Search'
            }


# Global MCP tools instance
mcp_tools = MCPTools()


# Convenience functions
async def create_calendar_event(summary: str, date_str: str) -> Dict[str, Any]:
    """Convenience function to create calendar event"""
    return await mcp_tools.create_event(summary, date_str)


async def send_email_notification(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Convenience function to send email"""
    return await mcp_tools.send_email(to, subject, body)


async def search_web(query: str, max_results: int = 3) -> Dict[str, Any]:
    """Convenience function to search web"""
    return await mcp_tools.web_search(query, max_results)


async def check_all_mcp_health() -> Dict[str, Any]:
    """Check health of all MCP tools"""
    calendar_health = await mcp_tools.check_calendar_health()
    gmail_health = await mcp_tools.check_gmail_health()
    search_health = await mcp_tools.check_search_health()
    
    return {
        'calendar': calendar_health,
        'gmail': gmail_health,
        'search': search_health
    }
