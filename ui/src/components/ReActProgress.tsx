import { useEffect, useState } from 'react';

interface ProgressStep {
  id: string;
  type: 'reasoning' | 'tool' | 'synthesis';
  status: 'pending' | 'active' | 'completed' | 'error';
  title: string;
  description?: string;
  timestamp?: string;
}

type Props = {
  steps: ProgressStep[];
  currentStep?: number;
  isComplete?: boolean;
};

const stepIcons = {
  reasoning: '🤔',
  tool: '🛠️',
  synthesis: '🔄'
};

const stepColors = {
  reasoning: 'var(--accent)',
  tool: 'var(--user)', 
  synthesis: 'var(--assistant)'
};

export function ReActProgress({ steps, currentStep = 0, isComplete = false }: Props) {
  const [animatedSteps, setAnimatedSteps] = useState<ProgressStep[]>(steps);

  useEffect(() => {
    // Animate step completion
    const timer = setTimeout(() => {
      setAnimatedSteps(steps);
    }, 100);
    return () => clearTimeout(timer);
  }, [steps]);

  if (steps.length === 0) {
    return null;
  }

  return (
    <div className="react-progress">
      <div className="progress-header">
        <span className="progress-title">
          {isComplete ? '✅ ReAct Process Complete' : '🧠 ReAct Agent Working...'}
        </span>
        <span className="progress-counter">
          Step {Math.min(currentStep + 1, steps.length)} of {steps.length}
        </span>
      </div>
      
      <div className="progress-timeline">
        {animatedSteps.map((step, index) => (
          <div 
            key={step.id} 
            className={`progress-step ${step.type} ${step.status}`}
            style={{
              '--step-color': stepColors[step.type]
            } as React.CSSProperties}
          >
            <div className="step-connector">
              {index < steps.length - 1 && (
                <div className={`connector-line ${index < currentStep ? 'completed' : ''}`} />
              )}
            </div>
            
            <div className="step-icon">
              {step.status === 'active' ? (
                <div className="spinner-small" />
              ) : step.status === 'error' ? (
                '❌'
              ) : step.status === 'completed' ? (
                '✅'
              ) : (
                stepIcons[step.type]
              )}
            </div>
            
            <div className="step-content">
              <div className="step-title">{step.title}</div>
              {step.description && (
                <div className="step-description">{step.description}</div>
              )}
              {step.timestamp && step.status === 'completed' && (
                <div className="step-timestamp">{step.timestamp}</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Hook for managing ReAct progress state
export function useReActProgress() {
  const [steps, setSteps] = useState<ProgressStep[]>([]);
  const [currentStep, setCurrentStep] = useState(0);
  const [isComplete, setIsComplete] = useState(false);

  const addStep = (step: Omit<ProgressStep, 'id'>) => {
    const newStep: ProgressStep = {
      ...step,
      id: `step-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    };
    setSteps(prev => [...prev, newStep]);
  };

  const updateStep = (id: string, updates: Partial<ProgressStep>) => {
    setSteps(prev => prev.map(step => 
      step.id === id ? { ...step, ...updates } : step
    ));
  };

  const completeStep = (id: string) => {
    updateStep(id, { 
      status: 'completed', 
      timestamp: new Date().toLocaleTimeString() 
    });
    setCurrentStep(prev => prev + 1);
  };

  const setStepActive = (id: string) => {
    updateStep(id, { status: 'active' });
  };

  const setStepError = (id: string, error: string) => {
    updateStep(id, { 
      status: 'error', 
      description: error 
    });
  };

  const reset = () => {
    setSteps([]);
    setCurrentStep(0);
    setIsComplete(false);
  };

  const complete = () => {
    setIsComplete(true);
  };

  return {
    steps,
    currentStep,
    isComplete,
    addStep,
    updateStep,
    completeStep,
    setStepActive,
    setStepError,
    reset,
    complete
  };
}