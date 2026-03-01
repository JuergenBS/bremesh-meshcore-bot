#!/usr/bin/env python3
"""
Services API Module
Handles API endpoints for external service integrations (HBME Ingestor, etc.)
"""

import asyncio
from datetime import datetime
from flask import jsonify, request


class ServicesAPI:
    """Handles Services API endpoints for external integrations."""
    
    def __init__(self, app, db_manager, logger, bot_instance=None):
        """Initialize Services API.
        
        Args:
            app: Flask application instance
            db_manager: Database manager instance
            logger: Logger instance
            bot_instance: Optional bot instance for service access
        """
        self.app = app
        self.db_manager = db_manager
        self.logger = logger
        self.bot = bot_instance
        self._register_routes()
    
    def set_bot_instance(self, bot):
        """Set bot instance for service access.
        
        Args:
            bot: The bot instance.
        """
        self.bot = bot
    
    def _register_routes(self):
        """Register all API routes."""
        
        # ─────────────────────────────────────────────────────────────────────
        # HBME Ingestor Service
        # ─────────────────────────────────────────────────────────────────────
        
        @self.app.route('/api/services/hbme/config')
        def api_hbme_config():
            """Get HBME Ingestor configuration."""
            return self._get_hbme_config()
        
        @self.app.route('/api/services/hbme/config', methods=['POST'])
        def api_hbme_save_config():
            """Save HBME Ingestor configuration."""
            return self._save_hbme_config()
        
        @self.app.route('/api/services/hbme/toggle', methods=['POST'])
        def api_hbme_toggle():
            """Toggle HBME Ingestor service."""
            return self._toggle_hbme()
        
        @self.app.route('/api/services/hbme/test', methods=['POST'])
        def api_hbme_test():
            """Test HBME Ingestor connection."""
            return self._test_hbme()
        
        @self.app.route('/api/services/hbme/stats')
        def api_hbme_stats():
            """Get HBME Ingestor statistics."""
            return self._get_hbme_stats()
        
        @self.app.route('/api/services/hbme/preview')
        def api_hbme_preview():
            """Get preview packets."""
            return self._get_hbme_preview()
        
        @self.app.route('/api/services/hbme/preview/clear', methods=['POST'])
        def api_hbme_preview_clear():
            """Clear preview queue."""
            return self._clear_hbme_preview()
        
        @self.app.route('/api/services/hbme/preview-mode', methods=['POST'])
        def api_hbme_preview_mode():
            """Toggle preview mode."""
            return self._toggle_hbme_preview_mode()
        
        @self.app.route('/api/services/hbme/clear-error', methods=['POST'])
        def api_hbme_clear_error():
            """Clear last error."""
            return self._clear_hbme_error()
        
        # ─────────────────────────────────────────────────────────────────────
        # General Services Overview
        # ─────────────────────────────────────────────────────────────────────
        
        @self.app.route('/api/services/overview')
        def api_services_overview():
            """Get overview of all external services."""
            return self._get_services_overview()
    
    # ─────────────────────────────────────────────────────────────────────────
    # HBME Ingestor Methods
    # ─────────────────────────────────────────────────────────────────────────
    
    def _get_hbme_config(self):
        """Get HBME Ingestor configuration."""
        try:
            # Get from database first, fallback to defaults
            enabled = self.db_manager.get_metadata('hbme_ingestor_enabled')
            api_url = self.db_manager.get_metadata('hbme_ingestor_api_url')
            auth_url = self.db_manager.get_metadata('hbme_ingestor_auth_url')
            username = self.db_manager.get_metadata('hbme_ingestor_username')
            password = self.db_manager.get_metadata('hbme_ingestor_password')
            preview_mode = self.db_manager.get_metadata('hbme_ingestor_preview_mode')
            
            # Default values
            default_url = 'https://api.hbme.sh/ingestor/auth/packet'
            default_auth_url = 'https://auth.hbme.sh/api/firstfactor'
            
            return jsonify({
                'enabled': enabled == 'true' if enabled else False,
                'preview_mode': preview_mode == 'true' if preview_mode is not None else True,
                'api_url': api_url or default_url,
                'auth_url': auth_url or default_auth_url,
                'has_credentials': bool(username and password),
                'username': username or ''
            })
        except Exception as e:
            self.logger.error(f"Error getting HBME config: {e}")
            return jsonify({'error': str(e)}), 500
    
    def _save_hbme_config(self):
        """Save HBME Ingestor configuration."""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            # Save API URL
            if 'api_url' in data:
                api_url = data['api_url'].strip()
                if api_url:
                    self.db_manager.set_metadata('hbme_ingestor_api_url', api_url)
            
            # Save Auth URL
            if 'auth_url' in data:
                auth_url = data['auth_url'].strip()
                if auth_url:
                    self.db_manager.set_metadata('hbme_ingestor_auth_url', auth_url)
            
            # Save Username
            if 'username' in data:
                username = data['username'].strip()
                if username:
                    self.db_manager.set_metadata('hbme_ingestor_username', username)
            
            # Save Password (only if provided, not empty)
            if 'password' in data:
                password = data['password'].strip()
                if password:
                    self.db_manager.set_metadata('hbme_ingestor_password', password)
            
            # Reload service config if running
            self._reload_hbme_service()
            
            return jsonify({
                'success': True,
                'message': 'Konfiguration gespeichert'
            })
        except Exception as e:
            self.logger.error(f"Error saving HBME config: {e}")
            return jsonify({'error': str(e)}), 500
    
    def _toggle_hbme(self):
        """Toggle HBME Ingestor service."""
        try:
            data = request.get_json() or {}
            
            # Get current state
            current = self.db_manager.get_metadata('hbme_ingestor_enabled')
            current_enabled = current == 'true' if current else False
            
            # Toggle or set explicitly
            if 'enabled' in data:
                new_enabled = data['enabled']
            else:
                new_enabled = not current_enabled
            
            # Check if credentials exist before enabling
            if new_enabled:
                username = self.db_manager.get_metadata('hbme_ingestor_username')
                password = self.db_manager.get_metadata('hbme_ingestor_password')
                if not username or not password:
                    return jsonify({
                        'success': False,
                        'message': 'Bitte zuerst Zugangsdaten (Username & Passwort) konfigurieren',
                        'enabled': False
                    })
            
            # Save new state
            self.db_manager.set_metadata('hbme_ingestor_enabled', 'true' if new_enabled else 'false')
            
            # Start/stop service if bot is available
            if self.bot:
                try:
                    loop = self.bot.loop if hasattr(self.bot, 'loop') else asyncio.get_event_loop()
                    asyncio.run_coroutine_threadsafe(
                        self._manage_hbme_service(new_enabled),
                        loop
                    )
                except Exception as e:
                    self.logger.warning(f"Could not manage service lifecycle: {e}")
            
            return jsonify({
                'success': True,
                'enabled': new_enabled,
                'message': 'Service aktiviert' if new_enabled else 'Service deaktiviert'
            })
        except Exception as e:
            self.logger.error(f"Error toggling HBME service: {e}")
            return jsonify({'error': str(e)}), 500
    
    def _test_hbme(self):
        """Test HBME Ingestor connection with Authelia SSO."""
        import aiohttp
        import time
        import hashlib
        
        try:
            data = request.get_json() or {}
            
            # Get test parameters
            api_url = data.get('api_url') or self.db_manager.get_metadata('hbme_ingestor_api_url')
            auth_url = data.get('auth_url') or self.db_manager.get_metadata('hbme_ingestor_auth_url')
            
            # Always get credentials from database - never from frontend
            username = self.db_manager.get_metadata('hbme_ingestor_username')
            password = self.db_manager.get_metadata('hbme_ingestor_password')
            
            if not api_url:
                api_url = 'https://api.hbme.sh/ingestor/auth/packet'
            if not auth_url:
                auth_url = 'https://auth.hbme.sh/api/firstfactor'
            
            if not username or not password:
                return jsonify({
                    'success': False,
                    'message': 'Keine Zugangsdaten konfiguriert',
                    'response_time': 0
                })
            
            # Try to get a real packet from preview queue in DB
            test_payload = None
            try:
                import json
                preview_data = self.db_manager.get_metadata('hbme_preview_queue')
                if preview_data:
                    packets = json.loads(preview_data)
                    if packets:
                        test_payload = packets[-1].get('data')
            except Exception as e:
                self.logger.debug(f"Could not load preview packet: {e}")
            
            # Fallback to synthetic payload
            if not test_payload:
                test_hash = hashlib.sha256(f"test_{time.time()}".encode()).hexdigest()
                test_payload = {
                    'route_type': 'ROUTE_TYPE_FLOOD',
                    'payload_type': 'PAYLOAD_TYPE_ADVERT',
                    'snr': -5.0,
                    'rssi': -95,
                    'path': 'aabbcc',
                    'path_len': 3,
                    'hash': test_hash
                }
            
            # Direct async test with Authelia SSO
            async def do_test():
                cookie_jar = aiohttp.CookieJar(unsafe=True)
                try:
                    async with aiohttp.ClientSession(
                        timeout=aiohttp.ClientTimeout(total=10),
                        cookie_jar=cookie_jar
                    ) as session:
                        # Step 1: Authenticate with Authelia
                        auth_payload = {
                            'username': username,
                            'password': password,
                            'keepMeLoggedIn': False
                        }
                        
                        start_time = time.time()
                        
                        async with session.post(
                            auth_url,
                            json=auth_payload,
                            headers={'Content-Type': 'application/json'}
                        ) as auth_response:
                            auth_elapsed = time.time() - start_time
                            
                            if auth_response.status == 401:
                                return {
                                    'success': False,
                                    'message': 'Anmeldung fehlgeschlagen: Ung\u00fcltige Zugangsdaten',
                                    'response_time': round(auth_elapsed * 1000)
                                }
                            elif auth_response.status != 200:
                                return {
                                    'success': False,
                                    'message': f'Authelia Fehler: HTTP {auth_response.status}',
                                    'response_time': round(auth_elapsed * 1000)
                                }
                            
                            # Check Authelia response
                            try:
                                import json as json_mod
                                auth_text = await auth_response.text()
                                auth_result = json_mod.loads(auth_text)
                                auth_status = auth_result.get('status', '')
                                if auth_status and auth_status != 'OK':
                                    return {
                                        'success': False,
                                        'message': f'Authelia Status: {auth_status}',
                                        'response_time': round(auth_elapsed * 1000)
                                    }
                            except (json.JSONDecodeError, Exception):
                                pass
                        
                        # Step 2: Send test packet with session cookie
                        start_time = time.time()
                        
                        async with session.post(
                            api_url,
                            json=test_payload,
                            headers={'Content-Type': 'application/json'}
                        ) as response:
                            elapsed = time.time() - start_time
                            response_text = await response.text()
                            
                            if response.status == 200:
                                return {
                                    'success': True,
                                    'message': 'Anmeldung & Verbindung erfolgreich',
                                    'response_time': round((auth_elapsed + elapsed) * 1000)
                                }
                            elif response.status == 400 and 'duplicat' in response_text.lower():
                                return {
                                    'success': True,
                                    'message': 'Verbindung erfolgreich (Testpaket war Duplikat)',
                                    'response_time': round((auth_elapsed + elapsed) * 1000)
                                }
                            elif response.status in (401, 403):
                                return {
                                    'success': False,
                                    'message': 'Anmeldung OK, aber API-Zugriff verweigert',
                                    'response_time': round((auth_elapsed + elapsed) * 1000)
                                }
                            else:
                                return {
                                    'success': False,
                                    'message': f'API-Fehler: HTTP {response.status}',
                                    'response_time': round((auth_elapsed + elapsed) * 1000)
                                }
                except asyncio.TimeoutError:
                    return {
                        'success': False,
                        'message': 'Timeout - Server antwortet nicht',
                        'response_time': 10000
                    }
                except Exception as e:
                    return {
                        'success': False,
                        'message': f'Verbindungsfehler: {str(e)[:100]}',
                        'response_time': 0
                    }
            
            # Run the async test
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(do_test())
            finally:
                loop.close()
            
            return jsonify(result)
                
        except Exception as e:
            self.logger.error(f"Error testing HBME connection: {e}")
            return jsonify({
                'success': False,
                'message': f'Fehler: {str(e)[:100]}',
                'response_time': 0
            })
    
    def _get_hbme_stats(self):
        """Get HBME Ingestor statistics."""
        try:
            service = self._get_hbme_service()
            
            if service:
                # Direct access to service (in-process)
                stats = service.get_stats()
                return jsonify(stats)
            else:
                # Read from database (cross-process communication)
                db = self.db_manager
                
                enabled = db.get_metadata('hbme_ingestor_enabled')
                username = db.get_metadata('hbme_ingestor_username')
                password = db.get_metadata('hbme_ingestor_password')
                api_url = db.get_metadata('hbme_ingestor_api_url')
                auth_url = db.get_metadata('hbme_ingestor_auth_url')
                
                # Read stats from DB
                packets_sent = db.get_metadata('hbme_stats_packets_sent')
                packets_failed = db.get_metadata('hbme_stats_packets_failed')
                packets_captured = db.get_metadata('hbme_stats_packets_captured')
                running = db.get_metadata('hbme_stats_running')
                avg_response_ms = db.get_metadata('hbme_stats_avg_response_ms')
                last_send_time = db.get_metadata('hbme_stats_last_send_time')
                last_error = db.get_metadata('hbme_stats_last_error')
                last_error_time = db.get_metadata('hbme_stats_last_error_time')
                preview_mode = db.get_metadata('hbme_ingestor_preview_mode')
                
                return jsonify({
                    'enabled': enabled == 'true' if enabled else False,
                    'running': running == 'true' if running else False,
                    'preview_mode': preview_mode == 'true' if preview_mode is not None else True,
                    'api_url': api_url or 'https://api.hbme.sh/ingestor/auth/packet',
                    'auth_url': auth_url or 'https://auth.hbme.sh/api/firstfactor',
                    'has_credentials': bool(username and password),
                    'username': username or '',
                    'packets_sent': int(packets_sent) if packets_sent else 0,
                    'packets_failed': int(packets_failed) if packets_failed else 0,
                    'packets_captured': int(packets_captured) if packets_captured else 0,
                    'last_send_time': last_send_time,
                    'last_error': last_error,
                    'last_error_time': last_error_time,
                    'avg_response_time_ms': float(avg_response_ms) if avg_response_ms else 0
                })
        except Exception as e:
            self.logger.error(f"Error getting HBME stats: {e}")
            return jsonify({'error': str(e)}), 500
    
    def _get_hbme_service(self):
        """Get HBME Ingestor service instance from bot."""
        if not self.bot:
            return None
        
        # Check in services dict
        if hasattr(self.bot, 'services') and isinstance(self.bot.services, dict):
            if 'hbmeingestor' in self.bot.services:
                return self.bot.services['hbmeingestor']
            for name, service in self.bot.services.items():
                if service.__class__.__name__ == 'HBMEIngestorService':
                    return service
        
        # Fallback: check in service_plugins list (legacy)
        if hasattr(self.bot, 'service_plugins'):
            for service in self.bot.service_plugins:
                if service.__class__.__name__ == 'HBMEIngestorService':
                    return service
        
        return None
    
    def _reload_hbme_service(self):
        """Reload HBME service configuration."""
        service = self._get_hbme_service()
        if service:
            service.reload_config()
    
    async def _manage_hbme_service(self, enable: bool):
        """Start or stop HBME service."""
        service = self._get_hbme_service()
        if service:
            service.reload_config()
            if enable and not service._running:
                await service.start()
            elif not enable and service._running:
                await service.stop()
    
    def _get_hbme_preview(self):
        """Get preview packets from HBME Ingestor."""
        try:
            import json
            limit = request.args.get('limit', 20, type=int)
            service = self._get_hbme_service()
            
            if service:
                packets = service.get_preview_packets(limit)
                return jsonify({
                    'packets': packets,
                    'total': len(service.preview_queue),
                    'preview_mode': service.preview_mode
                })
            else:
                # Read from database (cross-process)
                db = self.db_manager
                preview_queue_json = db.get_metadata('hbme_preview_queue')
                preview_mode = db.get_metadata('hbme_ingestor_preview_mode')
                
                packets = []
                if preview_queue_json:
                    try:
                        all_packets = json.loads(preview_queue_json)
                        packets = list(reversed(all_packets))[:limit]
                    except json.JSONDecodeError:
                        pass
                
                return jsonify({
                    'packets': packets,
                    'total': len(packets),
                    'preview_mode': preview_mode == 'true' if preview_mode is not None else True
                })
        except Exception as e:
            self.logger.error(f"Error getting HBME preview: {e}")
            return jsonify({'error': str(e)}), 500
    
    def _clear_hbme_preview(self):
        """Clear HBME preview queue."""
        try:
            service = self._get_hbme_service()
            
            if service:
                count = service.clear_preview_queue()
                self.db_manager.set_metadata('hbme_preview_queue', '[]')
                return jsonify({
                    'success': True,
                    'message': f'{count} Pakete gelöscht'
                })
            else:
                self.db_manager.set_metadata('hbme_preview_queue', '[]')
                return jsonify({
                    'success': True,
                    'message': 'Queue in Datenbank geleert'
                })
        except Exception as e:
            self.logger.error(f"Error clearing HBME preview: {e}")
            return jsonify({'error': str(e)}), 500
    
    def _toggle_hbme_preview_mode(self):
        """Toggle HBME preview mode."""
        try:
            data = request.get_json() or {}
            service = self._get_hbme_service()
            
            # Get current state from DB
            current = self.db_manager.get_metadata('hbme_ingestor_preview_mode')
            current_preview = current == 'true' if current is not None else True
            
            # Toggle or set explicitly
            if 'preview_mode' in data:
                new_preview = data['preview_mode']
            else:
                new_preview = not current_preview
            
            # Save to DB (single source of truth)
            self.db_manager.set_metadata('hbme_ingestor_preview_mode', 'true' if new_preview else 'false')
            
            # Update service if running
            if service:
                service.set_preview_mode(new_preview)
            
            return jsonify({
                'success': True,
                'preview_mode': new_preview,
                'message': 'TEST-Modus aktiviert' if new_preview else 'LIVE-Modus aktiviert - Pakete werden gesendet!'
            })
        except Exception as e:
            self.logger.error(f"Error toggling HBME preview mode: {e}")
            return jsonify({'error': str(e)}), 500
    
    def _clear_hbme_error(self):
        """Clear the last error from HBME Ingestor."""
        try:
            service = self._get_hbme_service()
            
            if service:
                service.clear_last_error()
            else:
                self.db_manager.set_metadata('hbme_stats_last_error', '')
                self.db_manager.set_metadata('hbme_stats_last_error_time', '')
            
            return jsonify({
                'success': True,
                'message': 'Letzter Fehler gelöscht'
            })
        except Exception as e:
            self.logger.error(f"Error clearing HBME error: {e}")
            return jsonify({'error': str(e)}), 500
    
    # ─────────────────────────────────────────────────────────────────────────
    # General Overview Methods
    # ─────────────────────────────────────────────────────────────────────────
    
    def _get_services_overview(self):
        """Get overview of all external services."""
        try:
            services = []
            db = self.db_manager
            
            # HBME Ingestor
            hbme_enabled = db.get_metadata('hbme_ingestor_enabled')
            hbme_running = db.get_metadata('hbme_stats_running')
            hbme_service = self._get_hbme_service()
            
            running = False
            if hbme_service:
                running = hbme_service._running
            elif hbme_running:
                running = hbme_running == 'true'
            
            services.append({
                'id': 'hbme',
                'name': 'HBME Paket Ingestor',
                'description': 'Sendet Paketdaten an die HBME API für Netzwerkanalyse',
                'enabled': hbme_enabled == 'true' if hbme_enabled else False,
                'running': running,
                'icon': 'fa-broadcast-tower'
            })
            
            return jsonify({
                'services': services,
                'total': len(services),
                'active': sum(1 for s in services if s['enabled'])
            })
        except Exception as e:
            self.logger.error(f"Error getting services overview: {e}")
            return jsonify({'error': str(e)}), 500
