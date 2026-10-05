"use client";

interface MailNexaLogoProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'indigo' | 'violet' | 'sky' | 'brand';
}

export default function MailNexaLogo({ size = 'sm', variant = 'brand' }: MailNexaLogoProps) {
  const dims = {
    xs: { box: 28, font: 11, shadow: 2 },
    sm: { box: 36, font: 14, shadow: 3 },
    md: { box: 48, font: 19, shadow: 4 },
    lg: { box: 72, font: 28, shadow: 5 },
    xl: { box: 96, font: 38, shadow: 7 },
  }[size];

  const gradientMap = {
    brand: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 40%, #3730a3 100%)',
    indigo: 'linear-gradient(135deg, #818cf8 0%, #4f46e5 50%, #3730a3 100%)',
    violet: 'linear-gradient(135deg, #c084fc 0%, #7c3aed 50%, #5b21b6 100%)',
    sky: 'linear-gradient(135deg, #38bdf8 0%, #0284c7 50%, #075985 100%)',
  };

  const shadowColorMap = {
    brand: 'rgba(79,70,229,0.5)',
    indigo: 'rgba(79,70,229,0.5)',
    violet: 'rgba(124,58,237,0.5)',
    sky: 'rgba(2,132,199,0.5)',
  };

  return (
    <div
      style={{
        width: dims.box,
        height: dims.box,
        position: 'relative',
        perspective: '400px',
        flexShrink: 0,
      }}
    >
      {/* 3D Cube Front Face */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: dims.box * 0.22,
          background: gradientMap[variant],
          boxShadow: `
            0 ${dims.shadow * 2}px ${dims.shadow * 5}px ${shadowColorMap[variant]},
            inset 0 1px 1px rgba(255,255,255,0.4),
            inset 0 -2px 4px rgba(0,0,0,0.3)
          `,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transform: 'translateZ(0)',
          zIndex: 3,
        }}
      >
        {/* MN Monogram SVG */}
        <svg
          width={dims.font * 1.8}
          height={dims.font * 1.4}
          viewBox="0 0 36 28"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* M Letter */}
          <path
            d="M2 24V4L10 16L18 4V24"
            stroke="white"
            strokeWidth="3.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {/* N Letter */}
          <path
            d="M22 24V4L34 24V4"
            stroke="rgba(255,255,255,0.75)"
            strokeWidth="3.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>

      {/* 3D Right Edge Shadow */}
      <div
        style={{
          position: 'absolute',
          top: dims.shadow,
          right: -dims.shadow,
          width: dims.shadow + 1,
          bottom: 0,
          borderRadius: `0 ${dims.shadow}px ${dims.shadow}px 0`,
          background: 'rgba(0,0,0,0.35)',
          zIndex: 2,
        }}
      />

      {/* 3D Bottom Edge Shadow */}
      <div
        style={{
          position: 'absolute',
          bottom: -dims.shadow,
          left: dims.shadow,
          right: 0,
          height: dims.shadow + 1,
          borderRadius: `0 0 ${dims.shadow}px ${dims.shadow}px`,
          background: 'rgba(0,0,0,0.25)',
          zIndex: 1,
        }}
      />
    </div>
  );
}
