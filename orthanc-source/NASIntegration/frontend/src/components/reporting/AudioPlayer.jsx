import React, { useState, useRef, useEffect } from 'react';
import { 
  Play, 
  Pause, 
  Square, 
  SkipBack, 
  SkipForward, 
  Volume2, 
  VolumeX,
  RotateCcw,
  FastForward,
  Rewind
} from 'lucide-react';

const AudioPlayer = ({ 
  sessionId, 
  audioUrl, 
  transcript = '', 
  onTimeUpdate, 
  onTranscriptClick,
  className = '' 
}) => {
  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleLoadedMetadata = () => {
      setDuration(audio.duration);
      setLoading(false);
    };

    const handleTimeUpdate = () => {
      const time = audio.currentTime;
      setCurrentTime(time);
      if (onTimeUpdate) {
        onTimeUpdate(time);
      }
    };

    const handleEnded = () => {
      setIsPlaying(false);
    };

    const handleError = (e) => {
      console.error('Audio error:', e);
      setError('Failed to load audio');
      setLoading(false);
    };

    const handleLoadStart = () => {
      setLoading(true);
      setError(null);
    };

    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('error', handleError);
    audio.addEventListener('loadstart', handleLoadStart);

    return () => {
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('error', handleError);
      audio.removeEventListener('loadstart', handleLoadStart);
    };
  }, [onTimeUpdate]);

  useEffect(() => {
    const audio = audioRef.current;
    if (audio) {
      audio.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  useEffect(() => {
    const audio = audioRef.current;
    if (audio) {
      audio.playbackRate = playbackRate;
    }
  }, [playbackRate]);

  const togglePlayPause = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      audio.play().then(() => {
        setIsPlaying(true);
      }).catch((err) => {
        console.error('Play failed:', err);
        setError('Failed to play audio');
      });
    }
  };

  const handleStop = () => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.pause();
    audio.currentTime = 0;
    setIsPlaying(false);
    setCurrentTime(0);
  };

  const handleSeek = (e) => {
    const audio = audioRef.current;
    if (!audio || !duration) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    const newTime = percent * duration;
    
    audio.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const skipTime = (seconds) => {
    const audio = audioRef.current;
    if (!audio) return;

    const newTime = Math.max(0, Math.min(duration, currentTime + seconds));
    audio.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const handleVolumeChange = (e) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    setIsMuted(newVolume === 0);
  };

  const toggleMute = () => {
    setIsMuted(!isMuted);
  };

  const handleSpeedChange = (newRate) => {
    setPlaybackRate(newRate);
  };

  const formatTime = (time) => {
    if (!time || !isFinite(time)) return '0:00';
    
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const getProgressPercent = () => {
    if (!duration) return 0;
    return (currentTime / duration) * 100;
  };

  if (error) {
    return (
      <div className={`bg-red-50 border border-red-200 rounded-lg p-4 ${className}`}>
        <div className="text-red-800 text-sm">{error}</div>
      </div>
    );
  }

  return (
    <div className={`bg-white border border-gray-200 rounded-lg p-4 ${className}`}>
      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        src={audioUrl}
        preload="metadata"
      />

      {/* Main Controls */}
      <div className="flex items-center space-x-4 mb-4">
        {/* Play/Pause/Stop */}
        <div className="flex items-center space-x-2">
          <button
            onClick={togglePlayPause}
            disabled={loading || !audioUrl}
            className="flex items-center justify-center w-12 h-12 bg-blue-600 text-white rounded-full hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
            ) : isPlaying ? (
              <Pause className="h-6 w-6" />
            ) : (
              <Play className="h-6 w-6 ml-1" />
            )}
          </button>
          
          <button
            onClick={handleStop}
            disabled={loading || !audioUrl}
            className="flex items-center justify-center w-10 h-10 bg-gray-600 text-white rounded-full hover:bg-gray-700 disabled:opacity-50"
          >
            <Square className="h-5 w-5" />
          </button>
        </div>

        {/* Skip Controls */}
        <div className="flex items-center space-x-1">
          <button
            onClick={() => skipTime(-10)}
            disabled={loading || !audioUrl}
            className="flex items-center justify-center w-8 h-8 bg-gray-100 text-gray-600 rounded hover:bg-gray-200 disabled:opacity-50"
            title="Skip back 10s"
          >
            <Rewind className="h-4 w-4" />
          </button>
          
          <button
            onClick={() => skipTime(-5)}
            disabled={loading || !audioUrl}
            className="flex items-center justify-center w-8 h-8 bg-gray-100 text-gray-600 rounded hover:bg-gray-200 disabled:opacity-50"
            title="Skip back 5s"
          >
            <SkipBack className="h-4 w-4" />
          </button>
          
          <button
            onClick={() => skipTime(5)}
            disabled={loading || !audioUrl}
            className="flex items-center justify-center w-8 h-8 bg-gray-100 text-gray-600 rounded hover:bg-gray-200 disabled:opacity-50"
            title="Skip forward 5s"
          >
            <SkipForward className="h-4 w-4" />
          </button>
          
          <button
            onClick={() => skipTime(10)}
            disabled={loading || !audioUrl}
            className="flex items-center justify-center w-8 h-8 bg-gray-100 text-gray-600 rounded hover:bg-gray-200 disabled:opacity-50"
            title="Skip forward 10s"
          >
            <FastForward className="h-4 w-4" />
          </button>
        </div>

        {/* Time Display */}
        <div className="text-sm text-gray-600 font-mono">
          {formatTime(currentTime)} / {formatTime(duration)}
        </div>

        {/* Speed Control */}
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-600">Speed:</span>
          <select
            value={playbackRate}
            onChange={(e) => handleSpeedChange(parseFloat(e.target.value))}
            className="text-sm border border-gray-300 rounded px-2 py-1"
            disabled={loading || !audioUrl}
          >
            <option value={0.5}>0.5x</option>
            <option value={0.75}>0.75x</option>
            <option value={1}>1x</option>
            <option value={1.25}>1.25x</option>
            <option value={1.5}>1.5x</option>
            <option value={2}>2x</option>
          </select>
        </div>

        {/* Volume Control */}
        <div className="flex items-center space-x-2">
          <button
            onClick={toggleMute}
            className="text-gray-600 hover:text-gray-800"
          >
            {isMuted || volume === 0 ? (
              <VolumeX className="h-5 w-5" />
            ) : (
              <Volume2 className="h-5 w-5" />
            )}
          </button>
          
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={isMuted ? 0 : volume}
            onChange={handleVolumeChange}
            className="w-20"
          />
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div
          className="w-full h-2 bg-gray-200 rounded-full cursor-pointer"
          onClick={handleSeek}
        >
          <div
            className="h-2 bg-blue-600 rounded-full transition-all duration-100"
            style={{ width: `${getProgressPercent()}%` }}
          />
        </div>
      </div>

      {/* Keyboard Shortcuts Help */}
      <div className="text-xs text-gray-500">
        <span className="font-medium">Shortcuts:</span> Space = Play/Pause, ← → = Skip 5s, ↑ ↓ = Volume
      </div>
    </div>
  );
};

export default AudioPlayer;