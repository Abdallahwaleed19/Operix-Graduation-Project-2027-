import React from 'react';
import { useTheme } from '../../context/ThemeContext';
import logoLight from '../../assets/logo-light.jpg';
import logoDark from '../../assets/logo-dark.jpg';

/**
 * Operix Unified Brand Logo Component
 * - Automatically switches between Light and Dark mode logo assets
 * - Preserves aspect ratio (1:1) and crisp resolution
 * - Provides optional brand typography label
 */
export default function Logo({
  size = 40,
  showText = true,
  subtitle = 'Industrial AI',
  className = '',
  style = {},
  alt = 'Operix Industrial AI'
}) {
  const { isDark } = useTheme();
  const currentLogo = isDark ? logoDark : logoLight;

  return (
    <div
      className={`operix-brand-unit ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '12px',
        textDecoration: 'none',
        ...style
      }}
    >
      <div
        className="operix-logo-img-wrapper"
        style={{
          width: typeof size === 'number' ? `${size}px` : size,
          height: typeof size === 'number' ? `${size}px` : size,
          borderRadius: typeof size === 'number' && size >= 48 ? '12px' : '9px',
          overflow: 'hidden',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: isDark
            ? '0 0 12px rgba(56, 189, 248, 0.2), 0 2px 6px rgba(0, 0, 0, 0.5)'
            : '0 2px 6px rgba(15, 23, 42, 0.08)',
          border: isDark
            ? '1px solid rgba(56, 189, 248, 0.25)'
            : '1px solid rgba(226, 232, 240, 0.9)',
          backgroundColor: isDark ? '#141E28' : '#F1F5F9',
          flexShrink: 0,
          transition: 'border-color 0.2s ease, box-shadow 0.2s ease'
        }}
      >
        <img
          src={currentLogo}
          alt={alt}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            aspectRatio: '1 / 1',
            display: 'block'
          }}
        />
      </div>

      {showText && (
        <div className="brand-title-group" style={{ display: 'flex', flexDirection: 'column' }}>
          <span
            className="brand-name"
            style={{
              fontSize: typeof size === 'number' && size >= 48 ? '24px' : '19px',
              fontWeight: 800,
              letterSpacing: '-0.02em',
              color: 'var(--text-primary)',
              lineHeight: 1.15
            }}
          >
            Operix
          </span>
          {subtitle && (
            <span
              className="brand-sub"
              style={{
                fontSize: typeof size === 'number' && size >= 48 ? '11px' : '10px',
                fontWeight: 700,
                letterSpacing: '0.1em',
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                marginTop: '1px'
              }}
            >
              {subtitle}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
