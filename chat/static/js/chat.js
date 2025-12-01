// WebRTC Audio Call Implementation

class AudioCallManager {
    constructor(chatSocket, currentUsername) {
        this.chatSocket = chatSocket;
        this.currentUsername = currentUsername;
        this.peerConnection = null;
        this.localStream = null;
        this.remoteUsername = null;
        this.isCallActive = false;
        this.isCaller = false;

        // WebRTC configuration with STUN servers
        this.rtcConfig = {
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ]
        };

        // Audio constraints for better quality
        this.audioConstraints = {
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true
            },
            video: false
        };

        this.setupEventListeners();
    }

    setupEventListeners() {
        // Call button clicks
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('call-user-btn')) {
                const targetUsername = e.target.dataset.username;
                this.initiateCall(targetUsername);
            }
        });

        // Accept call button
        const acceptBtn = document.getElementById('accept-call-btn');
        if (acceptBtn) {
            acceptBtn.addEventListener('click', () => this.acceptCall());
        }

        // Reject call button
        const rejectBtn = document.getElementById('reject-call-btn');
        if (rejectBtn) {
            rejectBtn.addEventListener('click', () => this.rejectCall());
        }

        // End call button
        const endCallBtn = document.getElementById('end-call-btn');
        if (endCallBtn) {
            endCallBtn.addEventListener('click', () => this.endCall());
        }

        // Mute button
        const muteBtn = document.getElementById('mute-btn');
        if (muteBtn) {
            muteBtn.addEventListener('click', () => this.toggleMute());
        }
    }

    async initiateCall(targetUsername) {
        if (this.isCallActive) {
            alert('You are already in a call');
            return;
        }

        this.remoteUsername = targetUsername;
        this.isCaller = true;

        try {
            // Request microphone access
            this.localStream = await navigator.mediaDevices.getUserMedia(this.audioConstraints);

            // Create peer connection
            this.createPeerConnection();

            // Add local stream to peer connection
            this.localStream.getTracks().forEach(track => {
                this.peerConnection.addTrack(track, this.localStream);
            });

            // Create and send offer
            const offer = await this.peerConnection.createOffer();
            await this.peerConnection.setLocalDescription(offer);

            // Send offer via WebSocket
            this.chatSocket.send(JSON.stringify({
                type: 'call_offer',
                target_username: targetUsername,
                offer: {
                    type: offer.type,
                    sdp: offer.sdp
                }
            }));

            this.showCallUI('Calling ' + targetUsername + '...', 'outgoing');

        } catch (error) {
            console.error('Error initiating call:', error);
            alert('Could not access microphone. Please check permissions.');
            this.cleanup();
        }
    }

    async handleCallOffer(caller, offer) {
        if (this.isCallActive) {
            // Send busy signal
            this.chatSocket.send(JSON.stringify({
                type: 'call_reject',
                target_username: caller
            }));
            return;
        }

        this.remoteUsername = caller;
        this.isCaller = false;

        // Show incoming call modal
        this.showIncomingCallModal(caller);

        // Store offer for when user accepts
        this.pendingOffer = offer;
    }

    async acceptCall() {
        try {
            // Hide incoming call modal
            this.hideIncomingCallModal();

            // Request microphone access
            this.localStream = await navigator.mediaDevices.getUserMedia(this.audioConstraints);

            // Create peer connection
            this.createPeerConnection();

            // Add local stream
            this.localStream.getTracks().forEach(track => {
                this.peerConnection.addTrack(track, this.localStream);
            });

            // Set remote description from offer
            await this.peerConnection.setRemoteDescription(new RTCSessionDescription(this.pendingOffer));

            // Create and send answer
            const answer = await this.peerConnection.createAnswer();
            await this.peerConnection.setLocalDescription(answer);

            this.chatSocket.send(JSON.stringify({
                type: 'call_answer',
                target_username: this.remoteUsername,
                answer: {
                    type: answer.type,
                    sdp: answer.sdp
                }
            }));

            this.showCallUI('Connected to ' + this.remoteUsername, 'active');
            this.isCallActive = true;

        } catch (error) {
            console.error('Error accepting call:', error);
            alert('Could not access microphone. Please check permissions.');
            this.cleanup();
        }
    }

    rejectCall() {
        this.hideIncomingCallModal();

        this.chatSocket.send(JSON.stringify({
            type: 'call_reject',
            target_username: this.remoteUsername
        }));

        this.cleanup();
    }

    async handleCallAnswer(answerer, answer) {
        try {
            await this.peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
            this.showCallUI('Connected to ' + answerer, 'active');
            this.isCallActive = true;
        } catch (error) {
            console.error('Error handling call answer:', error);
            this.endCall();
        }
    }

    async handleIceCandidate(sender, candidate) {
        try {
            if (this.peerConnection && candidate) {
                await this.peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
            }
        } catch (error) {
            console.error('Error adding ICE candidate:', error);
        }
    }

    handleCallReject() {
        alert(this.remoteUsername + ' rejected your call');
        this.cleanup();
    }

    handleCallEnd() {
        alert('Call ended by ' + this.remoteUsername);
        this.cleanup();
    }

    endCall() {
        if (this.remoteUsername) {
            this.chatSocket.send(JSON.stringify({
                type: 'call_end',
                target_username: this.remoteUsername
            }));
        }

        this.cleanup();
    }

    createPeerConnection() {
        this.peerConnection = new RTCPeerConnection(this.rtcConfig);

        // Handle ICE candidates
        this.peerConnection.onicecandidate = (event) => {
            if (event.candidate) {
                this.chatSocket.send(JSON.stringify({
                    type: 'call_ice_candidate',
                    target_username: this.remoteUsername,
                    candidate: {
                        candidate: event.candidate.candidate,
                        sdpMLineIndex: event.candidate.sdpMLineIndex,
                        sdpMid: event.candidate.sdpMid
                    }
                }));
            }
        };

        // Handle remote stream
        this.peerConnection.ontrack = (event) => {
            const remoteAudio = document.getElementById('remote-audio');
            if (remoteAudio) {
                remoteAudio.srcObject = event.streams[0];
            }
        };

        // Handle connection state changes
        this.peerConnection.onconnectionstatechange = () => {
            console.log('Connection state:', this.peerConnection.connectionState);
            if (this.peerConnection.connectionState === 'disconnected' ||
                this.peerConnection.connectionState === 'failed') {
                this.cleanup();
            }
        };
    }

    toggleMute() {
        if (this.localStream) {
            const audioTrack = this.localStream.getAudioTracks()[0];
            if (audioTrack) {
                audioTrack.enabled = !audioTrack.enabled;
                const muteBtn = document.getElementById('mute-btn');
                if (muteBtn) {
                    muteBtn.textContent = audioTrack.enabled ? '🔊 Mute' : '🔇 Unmute';
                    muteBtn.classList.toggle('muted', !audioTrack.enabled);
                }
            }
        }
    }

    showIncomingCallModal(caller) {
        const modal = document.getElementById('incoming-call-modal');
        const callerName = document.getElementById('caller-name');

        if (modal && callerName) {
            callerName.textContent = caller;
            modal.style.display = 'flex';

            // Play ringing sound (optional)
            // const ringtone = document.getElementById('ringtone');
            // if (ringtone) ringtone.play();
        }
    }

    hideIncomingCallModal() {
        const modal = document.getElementById('incoming-call-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    showCallUI(status, type) {
        const callWidget = document.getElementById('call-widget');
        const callStatus = document.getElementById('call-status');

        if (callWidget && callStatus) {
            callStatus.textContent = status;
            callWidget.style.display = 'block';
            callWidget.className = 'call-widget ' + type;

            if (type === 'active') {
                this.startCallTimer();
            }
        }
    }

    hideCallUI() {
        const callWidget = document.getElementById('call-widget');
        if (callWidget) {
            callWidget.style.display = 'none';
        }
        this.stopCallTimer();
    }

    startCallTimer() {
        let seconds = 0;
        const timerElement = document.getElementById('call-timer');

        this.callTimerInterval = setInterval(() => {
            seconds++;
            const mins = Math.floor(seconds / 60);
            const secs = seconds % 60;
            if (timerElement) {
                timerElement.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
            }
        }, 1000);
    }

    stopCallTimer() {
        if (this.callTimerInterval) {
            clearInterval(this.callTimerInterval);
            this.callTimerInterval = null;
        }
    }

    cleanup() {
        // Stop all tracks
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }

        // Close peer connection
        if (this.peerConnection) {
            this.peerConnection.close();
            this.peerConnection = null;
        }

        // Reset state
        this.isCallActive = false;
        this.remoteUsername = null;
        this.isCaller = false;
        this.pendingOffer = null;

        // Hide UI
        this.hideCallUI();
        this.hideIncomingCallModal();
    }
}

// Export for use in room template
window.AudioCallManager = AudioCallManager;
