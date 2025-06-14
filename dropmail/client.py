import json
import time
import random
import string
import asyncio
import aiohttp
from typing import List, Dict, Optional, Tuple, Set, Callable
import requests
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

from .exceptions import DropMailError, SessionExpiredError, NetworkError


class dropmailplus:
    SERVERS = [
        "https://mirror2.dropmail.info",
        "https://dropmail.me"
    ]
    
    DOMAINS = [
        "dropmail.me",
        "10mail.org",
        "yomail.info",
        "emltmp.com",
        "emlpro.com",
        "emlhub.com",
        "freeml.net",
        "spymail.one",
        "mailpwr.com",
        "mimimail.me",
        "10mail.xyz"
    ]
    
    def __init__(self, token: Optional[str] = None, timeout: int = 30):
        self.token = token or self._generate_token()
        self.timeout = timeout
        self.current_server = None
        self._find_working_server()
        self._read_messages = {}
        
    def _generate_token(self, length: int = 16) -> str:
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
    
    def _find_working_server(self):
        for server in self.SERVERS:
            if self._test_server(server):
                self.current_server = server
                return
        raise NetworkError("No working servers available")
    
    def _test_server(self, server: str) -> bool:
        try:
            url = f"{server}/api/graphql/{self.token}"
            query = {"query": "query { __typename }"}
            response = requests.post(url, json=query, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _request(self, query: str, variables: Optional[Dict] = None) -> Dict:
        for server in [self.current_server] + [s for s in self.SERVERS if s != self.current_server]:
            try:
                url = f"{server}/api/graphql/{self.token}"
                payload = {"query": query}
                if variables:
                    payload["variables"] = variables
                
                response = requests.post(url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                
                result = response.json()
                if "errors" in result:
                    error = result["errors"][0]
                    if error.get("message") == "session_not_found":
                        raise SessionExpiredError("Session has expired")
                    raise DropMailError(f"GraphQL error: {error.get('message', 'Unknown error')}")
                
                if server != self.current_server:
                    self.current_server = server
                    
                return result["data"]
                
            except requests.exceptions.RequestException:
                continue
                
        raise NetworkError("All servers failed")
    
    def create(self, domain: Optional[str] = None) -> Dict[str, any]:
        if domain and domain not in self.DOMAINS:
            raise ValueError(f"Domain {domain} not supported. Use one of: {', '.join(self.DOMAINS)}")

        # Получаем список доменов один раз
        domains_query = """
        query {
            domains {
                id
                name
            }
        }
        """
        domains_data = self._request(domains_query)
        domain_map = {d['name']: d['id'] for d in domains_data['domains']}

        query = """
        mutation($input: IntroduceSessionInput) {
            introduceSession(input: $input) {
                id
                expiresAt
                addresses {
                    address
                }
            }
        }
        """

        variables = {}
        if domain:
            # Используем ID домена вместо имени
            domain_id = domain_map.get(domain)
            if not domain_id:
                raise ValueError(f"Domain {domain} not found")
            variables = {"input": {"domainId": domain_id}}

        data = self._request(query, variables)
        session = data["introduceSession"]

        session_id = session["id"]
        self._read_messages[session_id] = set()

        return {
            "session_id": session_id,
            "email": session["addresses"][0]["address"],
            "emails": [addr["address"] for addr in session["addresses"]],
            "expires_at": session["expiresAt"]
        }
    
    def restore_session(self, session_id: str) -> Dict[str, any]:
        query = """
        query($id: ID!) {
            session(id: $id) {
                id
                expiresAt
                addresses {
                    address
                }
            }
        }
        """
        
        data = self._request(query, {"id": session_id})
        
        if data["session"] is None:
            raise SessionExpiredError("Session not found or expired")
            
        session = data["session"]
        self._read_messages[session_id] = set()
        
        return {
            "session_id": session["id"],
            "email": session["addresses"][0]["address"] if session["addresses"] else None,
            "emails": [addr["address"] for addr in session["addresses"]],
            "expires_at": session["expiresAt"]
        }
    
    def get_messages(self, session_id: str, only_new: bool = False) -> List[Dict]:
        query = """
        query($id: ID!) {
            session(id: $id) {
                mails {
                    rawSize
                    fromAddr
                    toAddr
                    downloadUrl
                    text
                    html
                    headerSubject
                    receivedAt
                }
            }
        }
        """
        
        data = self._request(query, {"id": session_id})
        
        if data["session"] is None:
            raise SessionExpiredError("Session not found or expired")
            
        messages = data["session"]["mails"]
        
        if only_new and session_id in self._read_messages:
            new_messages = []
            for msg in messages:
                msg_id = f"{msg['fromAddr']}_{msg['headerSubject']}_{msg.get('receivedAt', '')}"
                if msg_id not in self._read_messages[session_id]:
                    self._read_messages[session_id].add(msg_id)
                    new_messages.append(msg)
            return new_messages
        else:
            if session_id in self._read_messages:
                for msg in messages:
                    msg_id = f"{msg['fromAddr']}_{msg['headerSubject']}_{msg.get('receivedAt', '')}"
                    self._read_messages[session_id].add(msg_id)
                    
        return messages
    
    def wait_for_message(self, session_id: str, timeout: int = 300, 
                        poll_interval: int = 2, filter_func: Optional[Callable] = None,
                        only_new: bool = True) -> Optional[Dict]:
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            messages = self.get_messages(session_id, only_new=only_new)
            
            if filter_func:
                messages = [msg for msg in messages if filter_func(msg)]
                
            if messages:
                return messages[0]
                
            time.sleep(poll_interval)
            
        return None
    
    def wait_for_messages(self, session_id: str, count: int = 1, timeout: int = 300,
                         poll_interval: int = 2, filter_func: Optional[Callable] = None) -> List[Dict]:
        start_time = time.time()
        collected = []
        
        while time.time() - start_time < timeout and len(collected) < count:
            messages = self.get_messages(session_id, only_new=True)
            
            if filter_func:
                messages = [msg for msg in messages if filter_func(msg)]
                
            collected.extend(messages[:count - len(collected)])
            
            if len(collected) >= count:
                break
                
            time.sleep(poll_interval)
            
        return collected
    
    def get_all_sessions(self) -> List[Dict]:
        query = """
        query {
            sessions {
                id
                expiresAt
                addresses {
                    address
                }
                mails {
                    rawSize
                    fromAddr
                    toAddr
                    headerSubject
                }
            }
        }
        """
        
        data = self._request(query)
        return data.get("sessions", [])
    
    def filter_messages(self, messages: List[Dict], 
                       from_addr: Optional[str] = None,
                       subject_contains: Optional[str] = None,
                       text_contains: Optional[str] = None) -> List[Dict]:
        filtered = messages
        
        if from_addr:
            filtered = [msg for msg in filtered if from_addr.lower() in msg['fromAddr'].lower()]
            
        if subject_contains:
            filtered = [msg for msg in filtered if subject_contains.lower() in msg.get('headerSubject', '').lower()]
            
        if text_contains:
            filtered = [msg for msg in filtered if text_contains.lower() in (msg.get('text', '') or '').lower()]
            
        return filtered


class async_dropmailplus:
    SERVERS = dropmailplus.SERVERS
    DOMAINS = dropmailplus.DOMAINS
    
    def __init__(self, token: Optional[str] = None, timeout: int = 30):
        self.token = token or self._generate_token()
        self.timeout = timeout
        self.current_server = None
        self._read_messages = {}
        
    def _generate_token(self, length: int = 16) -> str:
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
    
    async def _find_working_server(self):
        for server in self.SERVERS:
            if await self._test_server(server):
                self.current_server = server
                return
        raise NetworkError("No working servers available")
    
    async def _test_server(self, server: str) -> bool:
        try:
            url = f"{server}/api/graphql/{self.token}"
            query = {"query": "query { __typename }"}
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=query, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    return response.status == 200
        except:
            return False
    
    async def _request(self, query: str, variables: Optional[Dict] = None) -> Dict:
        for server in [self.current_server] + [s for s in self.SERVERS if s != self.current_server]:
            try:
                url = f"{server}/api/graphql/{self.token}"
                payload = {"query": query}
                if variables:
                    payload["variables"] = variables
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                        response.raise_for_status()
                        result = await response.json()
                        
                        if "errors" in result:
                            error = result["errors"][0]
                            if error.get("message") == "session_not_found":
                                raise SessionExpiredError("Session has expired")
                            raise DropMailError(f"GraphQL error: {error.get('message', 'Unknown error')}")
                        
                        if server != self.current_server:
                            self.current_server = server
                            
                        return result["data"]
                        
            except aiohttp.ClientError:
                continue
                
        raise NetworkError("All servers failed")
    
    async def initialize(self):
        await self._find_working_server()
        return self
    
    async def create(self, domain: Optional[str] = None) -> Dict[str, any]:
        if domain and domain not in self.DOMAINS:
            raise ValueError(f"Domain {domain} not supported. Use one of: {', '.join(self.DOMAINS)}")
            
        query = """
        mutation($input: IntroduceSessionInput) {
            introduceSession(input: $input) {
                id
                expiresAt
                addresses {
                    address
                }
            }
        }
        """
        
        variables = {}
        if domain:
            variables = {"input": {"withAddress": domain}}
        
        data = await self._request(query, variables)
        session = data["introduceSession"]
        
        session_id = session["id"]
        self._read_messages[session_id] = set()
        
        return {
            "session_id": session_id,
            "email": session["addresses"][0]["address"],
            "emails": [addr["address"] for addr in session["addresses"]],
            "expires_at": session["expiresAt"]
        }
    
    async def get_messages(self, session_id: str, only_new: bool = False) -> List[Dict]:
        query = """
        query($id: ID!) {
            session(id: $id) {
                mails {
                    rawSize
                    fromAddr
                    toAddr
                    downloadUrl
                    text
                    html
                    headerSubject
                    receivedAt
                }
            }
        }
        """
        
        data = await self._request(query, {"id": session_id})
        
        if data["session"] is None:
            raise SessionExpiredError("Session not found or expired")
            
        messages = data["session"]["mails"]
        
        if only_new and session_id in self._read_messages:
            new_messages = []
            for msg in messages:
                msg_id = f"{msg['fromAddr']}_{msg['headerSubject']}_{msg.get('receivedAt', '')}"
                if msg_id not in self._read_messages[session_id]:
                    self._read_messages[session_id].add(msg_id)
                    new_messages.append(msg)
            return new_messages
        else:
            if session_id in self._read_messages:
                for msg in messages:
                    msg_id = f"{msg['fromAddr']}_{msg['headerSubject']}_{msg.get('receivedAt', '')}"
                    self._read_messages[session_id].add(msg_id)
                    
        return messages
    
    async def wait_for_message(self, session_id: str, timeout: int = 300, 
                              poll_interval: int = 2, filter_func: Optional[Callable] = None,
                              only_new: bool = True) -> Optional[Dict]:
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            messages = await self.get_messages(session_id, only_new=only_new)
            
            if filter_func:
                messages = [msg for msg in messages if filter_func(msg)]
                
            if messages:
                return messages[0]
                
            await asyncio.sleep(poll_interval)
            
        return None


def dropmail(wait: bool = False, timeout: int = 300, domain: Optional[str] = None,
             blocking: bool = True) -> Tuple[str, callable]:
    client = dropmailplus()
    session = client.create(domain=domain)
    email = session["email"]
    session_id = session["session_id"]
    
    def check_messages(only_new: bool = False, from_addr: Optional[str] = None,
                      subject_contains: Optional[str] = None):
        messages = client.get_messages(session_id, only_new=only_new)
        if from_addr or subject_contains:
            return client.filter_messages(messages, from_addr=from_addr, 
                                        subject_contains=subject_contains)
        return messages
    
    if wait:
        if blocking:
            message = client.wait_for_message(session_id, timeout)
            if message:
                return email, check_messages
        else:
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(client.wait_for_message, session_id, timeout)
            return email, lambda: future.result() if future.done() else check_messages()
    
    return email, check_messages


async def async_dropmail(wait: bool = False, timeout: int = 300, domain: Optional[str] = None):
    client = await async_dropmailplus().initialize()
    session = await client.create(domain=domain)
    email = session["email"]
    session_id = session["session_id"]
    
    async def check_messages(only_new: bool = False):
        return await client.get_messages(session_id, only_new=only_new)
    
    if wait:
        message = await client.wait_for_message(session_id, timeout)
        
    return email, check_messages