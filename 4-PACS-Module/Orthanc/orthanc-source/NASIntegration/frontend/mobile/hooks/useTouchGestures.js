/**
 * Touch Gesture Hook for Medical Imaging
 * Optimized for precise medical interactions
 */

import { useState, useRef, useCallback } from 'react';

export const useTouchGestures = ({
    onPinch,
    onPan,
    onTap,
    onDoubleTap,
    onLongPress,
    onSwipe
}) => {
    const [gestureState, setGestureState] = useState({
        isGesturing: false,
        isPanning: false,
        isPinching: false,
        swipeDirection: null,
        touchCount: 0
    });

    const touchDataRef = useRef({
        touches: [],
        lastTap: 0,
        longPressTimer: null,
        initialDistance: 0,
        initialCenter: { x: 0, y: 0 },
        lastPanPosition: { x: 0, y: 0 },
        swipeStartPosition: { x: 0, y: 0 },
        swipeStartTime: 0
    });

    // Configuration
    const config = {
        doubleTapDelay: 300,
        longPressDelay: 500,
        minSwipeDistance: 50,
        maxSwipeTime: 300,
        pinchThreshold: 10,
        panThreshold: 5
    };

    const getTouchDistance = (touch1, touch2) => {
        const dx = touch1.clientX - touch2.clientX;
        const dy = touch1.clientY - touch2.clientY;
        return Math.sqrt(dx * dx + dy * dy);
    };

    const getTouchCenter = (touch1, touch2) => {
        return {
            x: (touch1.clientX + touch2.clientX) / 2,
            y: (touch1.clientY + touch2.clientY) / 2
        };
    };

    const handleTouchStart = useCallback((event) => {
        event.preventDefault();
        
        const touches = Array.from(event.touches);
        touchDataRef.current.touches = touches;
        
        setGestureState(prev => ({
            ...prev,
            isGesturing: true,
            touchCount: touches.length,
            swipeDirection: null
        }));

        if (touches.length === 1) {
            const touch = touches[0];
            touchDataRef.current.lastPanPosition = { x: touch.clientX, y: touch.clientY };
            touchDataRef.current.swipeStartPosition = { x: touch.clientX, y: touch.clientY };
            touchDataRef.current.swipeStartTime = Date.now();

            // Handle tap detection
            const now = Date.now();
            const timeSinceLastTap = now - touchDataRef.current.lastTap;
            
            if (timeSinceLastTap < config.doubleTapDelay) {
                // Double tap detected
                clearTimeout(touchDataRef.current.longPressTimer);
                onDoubleTap?.(touch.clientX, touch.clientY);
                touchDataRef.current.lastTap = 0; // Reset to prevent triple tap
            } else {
                touchDataRef.current.lastTap = now;
                
                // Start long press timer
                touchDataRef.current.longPressTimer = setTimeout(() => {
                    onLongPress?.(touch.clientX, touch.clientY);
                }, config.longPressDelay);
            }
        } else if (touches.length === 2) {
            // Two-finger gesture (pinch/zoom)
            clearTimeout(touchDataRef.current.longPressTimer);
            
            const distance = getTouchDistance(touches[0], touches[1]);
            const center = getTouchCenter(touches[0], touches[1]);
            
            touchDataRef.current.initialDistance = distance;
            touchDataRef.current.initialCenter = center;
            
            setGestureState(prev => ({
                ...prev,
                isPinching: true
            }));
        }
    }, [onDoubleTap, onLongPress]);

    const handleTouchMove = useCallback((event) => {
        event.preventDefault();
        
        const touches = Array.from(event.touches);
        
        if (touches.length === 1) {
            const touch = touches[0];
            const lastPos = touchDataRef.current.lastPanPosition;
            
            const deltaX = touch.clientX - lastPos.x;
            const deltaY = touch.clientY - lastPos.y;
            const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
            
            // Clear long press if moved too much
            if (distance > config.panThreshold) {
                clearTimeout(touchDataRef.current.longPressTimer);
                
                setGestureState(prev => ({
                    ...prev,
                    isPanning: true
                }));
                
                onPan?.(deltaX, deltaY);
                touchDataRef.current.lastPanPosition = { x: touch.clientX, y: touch.clientY };
            }
        } else if (touches.length === 2) {
            // Handle pinch gesture
            const distance = getTouchDistance(touches[0], touches[1]);
            const center = getTouchCenter(touches[0], touches[1]);
            
            if (touchDataRef.current.initialDistance > 0) {
                const scale = distance / touchDataRef.current.initialDistance;
                
                if (Math.abs(distance - touchDataRef.current.initialDistance) > config.pinchThreshold) {
                    onPinch?.(scale, center);
                    touchDataRef.current.initialDistance = distance;
                }
            }
        }
    }, [onPan, onPinch]);

    const handleTouchEnd = useCallback((event) => {
        event.preventDefault();
        
        const touches = Array.from(event.touches);
        
        // Clear timers
        clearTimeout(touchDataRef.current.longPressTimer);
        
        // Handle swipe detection for single touch
        if (touchDataRef.current.touches.length === 1 && touches.length === 0) {
            const endTime = Date.now();
            const swipeTime = endTime - touchDataRef.current.swipeStartTime;
            
            if (swipeTime < config.maxSwipeTime) {
                const startPos = touchDataRef.current.swipeStartPosition;
                const endPos = touchDataRef.current.lastPanPosition;
                
                const deltaX = endPos.x - startPos.x;
                const deltaY = endPos.y - startPos.y;
                const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
                
                if (distance > config.minSwipeDistance) {
                    let swipeDirection = null;
                    
                    if (Math.abs(deltaX) > Math.abs(deltaY)) {
                        swipeDirection = deltaX > 0 ? 'right' : 'left';
                    } else {
                        swipeDirection = deltaY > 0 ? 'down' : 'up';
                    }
                    
                    setGestureState(prev => ({
                        ...prev,
                        swipeDirection
                    }));
                    
                    onSwipe?.(swipeDirection, { deltaX, deltaY, distance });
                }
            }
            
            // Handle single tap (if no pan occurred)
            if (!gestureState.isPanning && !gestureState.isPinching) {
                const timeSinceLastTap = Date.now() - touchDataRef.current.lastTap;
                if (timeSinceLastTap >= config.doubleTapDelay) {
                    const touch = touchDataRef.current.touches[0];
                    onTap?.(touch.clientX, touch.clientY);
                }
            }
        }
        
        // Reset gesture state
        if (touches.length === 0) {
            setGestureState({
                isGesturing: false,
                isPanning: false,
                isPinching: false,
                swipeDirection: null,
                touchCount: 0
            });
            
            touchDataRef.current.initialDistance = 0;
        } else {
            setGestureState(prev => ({
                ...prev,
                touchCount: touches.length,
                isPanning: false,
                isPinching: touches.length === 2
            }));
        }
        
        touchDataRef.current.touches = touches;
    }, [gestureState.isPanning, gestureState.isPinching, onTap, onSwipe]);

    // Prevent context menu on long press (mobile browsers)
    const handleContextMenu = useCallback((event) => {
        event.preventDefault();
    }, []);

    return {
        onTouchStart: handleTouchStart,
        onTouchMove: handleTouchMove,
        onTouchEnd: handleTouchEnd,
        onContextMenu: handleContextMenu,
        gestureState
    };
};