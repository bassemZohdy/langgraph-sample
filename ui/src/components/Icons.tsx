import React from 'react';

type Props = { size?: number; className?: string };

export const SunIcon = ({ size = 18, className }: Props) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <circle cx="12" cy="12" r="4"/>
    <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>
  </svg>
);

export const MoonIcon = ({ size = 18, className }: Props) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
  </svg>
);

export const MonitorIcon = ({ size = 18, className }: Props) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <rect x="2" y="3" width="20" height="14" rx="2"/>
    <path d="M8 21h8M12 17v4"/>
  </svg>
);

export const SidebarOpenIcon = ({ size = 18, className }: Props) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <rect x="3" y="4" width="18" height="16" rx="2"/>
    <path d="M9 4v16"/>
  </svg>
);

export const SidebarClosedIcon = ({ size = 18, className }: Props) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <rect x="3" y="4" width="18" height="16" rx="2"/>
    <path d="M15 4v16"/>
  </svg>
);

export const EyeIcon = ({ size = 18, className }: Props) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/>
    <circle cx="12" cy="12" r="3"/>
  </svg>
);

export const EyeOffIcon = ({ size = 18, className }: Props) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <path d="M17.94 17.94A10.94 10.94 0 0112 20c-7 0-11-8-11-8a18.2 18.2 0 014.38-5.56"/>
    <path d="M9.9 4.24A10.94 10.94 0 0112 4c7 0 11 8 11 8a18.2 18.2 0 01-4.35 5.5"/>
    <path d="M14.12 14.12A3 3 0 019.88 9.88"/>
    <path d="M1 1l22 22"/>
  </svg>
);

export const StopIcon = ({ size = 18, className }: Props) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>
    <rect x="6" y="6" width="12" height="12" rx="2"/>
  </svg>
);

