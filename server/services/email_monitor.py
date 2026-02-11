"""
Email Monitor - Background email polling service
Location: server/services/email_monitor.py
"""
import logging
import asyncio
from typing import Dict, Any
from datetime import datetime

from server.managers.account_manager import AccountManager
from server.managers.email_manager import EmailManager
from server.intelligence.context_engine import ContextEngine

logger = logging.getLogger("email_monitor")


class EmailMonitor:
    """Background service for email monitoring"""
    
    def __init__(self, account_mgr: AccountManager, email_mgr: EmailManager, 
                 context_engine: ContextEngine, poll_interval: int = 180):
        self.account_mgr = account_mgr
        self.email_mgr = email_mgr
        self.context_engine = context_engine
        self.poll_interval = poll_interval
        self.running = False
        
    async def start(self):
        """Start monitoring"""
        self.running = True
        logger.info(f"Email monitor started (polling every {self.poll_interval}s)")
        
        while self.running:
            try:
                await self._poll_all_accounts()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                await asyncio.sleep(60)
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        logger.info("Email monitor stopped")
    
    async def _poll_all_accounts(self):
        """Poll all accounts for new emails"""
        result = self.email_mgr.check_all_accounts()
        
        if result["priority_messages"]:
            logger.info(f"Found {len(result['priority_messages'])} priority messages")
            # TODO: Trigger notifications
        
        logger.debug(f"Polled {len(result['by_account'])} accounts, {result['total_new']} new messages")