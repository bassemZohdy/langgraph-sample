import { useState, useEffect } from 'react';

interface ReActSettings {
  showReasoningSteps: boolean;
  enableReActMode: boolean;
  maxIterations: number;
}

const defaultSettings: ReActSettings = {
  showReasoningSteps: true,
  enableReActMode: true,
  maxIterations: 5
};

type Props = {
  onSettingsChange?: (settings: ReActSettings) => void;
};

export function ReActSettings({ onSettingsChange }: Props) {
  const [settings, setSettings] = useState<ReActSettings>(() => {
    const saved = localStorage.getItem('react-settings');
    return saved ? { ...defaultSettings, ...JSON.parse(saved) } : defaultSettings;
  });

  useEffect(() => {
    localStorage.setItem('react-settings', JSON.stringify(settings));
    onSettingsChange?.(settings);
  }, [settings, onSettingsChange]);

  const updateSetting = <K extends keyof ReActSettings>(key: K, value: ReActSettings[K]) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="react-settings">
      <div className="settings-header">
        <h3>🧠 ReAct Agent</h3>
      </div>
      
      <div className="setting-group">
        <div className="setting-item">
          <div className="setting-info">
            <span 
              className="setting-label" 
              title="Use multi-step reasoning and tool execution for comprehensive responses"
            >
              Enable ReAct Mode
            </span>
          </div>
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={settings.enableReActMode}
              onChange={(e) => updateSetting('enableReActMode', e.target.checked)}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>

        <div className="setting-item">
          <div className="setting-info">
            <span 
              className={`setting-label ${!settings.enableReActMode ? 'disabled' : ''}`}
              title="Display the agent's thinking process and tool usage in chat"
            >
              Show Reasoning Steps
            </span>
          </div>
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={settings.showReasoningSteps}
              onChange={(e) => updateSetting('showReasoningSteps', e.target.checked)}
              disabled={!settings.enableReActMode}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>

        <div className="setting-item range-setting">
          <div className="setting-info">
            <span 
              className={`setting-label ${!settings.enableReActMode ? 'disabled' : ''}`}
              title="Maximum number of reasoning iterations (1-10). Higher values allow more thorough analysis but take longer."
            >
              Max Reasoning Steps
            </span>
          </div>
          <div className="range-control">
            <input
              type="range"
              min="1"
              max="10"
              value={settings.maxIterations}
              onChange={(e) => updateSetting('maxIterations', parseInt(e.target.value))}
              disabled={!settings.enableReActMode}
              className="range-slider"
            />
            <span className="range-value">{settings.maxIterations}</span>
          </div>
        </div>
      </div>

      <div className="react-info">
        <div className="info-item">
          <span className="info-icon">⚡</span>
          <span className="info-text">
            <strong>Simple Mode:</strong> Fast direct responses
          </span>
        </div>
        <div className="info-item">
          <span className="info-icon">🧠</span>
          <span className="info-text">
            <strong>ReAct Mode:</strong> Reasoning + tools for comprehensive analysis
          </span>
        </div>
      </div>
    </div>
  );
}

// Hook to use ReAct settings
export function useReActSettings() {
  const [settings, setSettings] = useState<ReActSettings>(() => {
    const saved = localStorage.getItem('react-settings');
    return saved ? { ...defaultSettings, ...JSON.parse(saved) } : defaultSettings;
  });

  useEffect(() => {
    const handleStorageChange = () => {
      const saved = localStorage.getItem('react-settings');
      if (saved) {
        setSettings({ ...defaultSettings, ...JSON.parse(saved) });
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  return settings;
}