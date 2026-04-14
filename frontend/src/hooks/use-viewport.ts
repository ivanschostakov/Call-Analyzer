import { useEffect, useState } from 'react';

type ViewportMode = 'mobile' | 'tablet' | 'desktop';

export const MOBILE_MAX_WIDTH = 720;
export const TABLET_MAX_WIDTH = 1180;

function readWidth() {
  if (typeof window === 'undefined') {
    return 1440;
  }
  return window.innerWidth;
}

function toMode(width: number): ViewportMode {
  if (width <= MOBILE_MAX_WIDTH) {
    return 'mobile';
  }
  if (width <= TABLET_MAX_WIDTH) {
    return 'tablet';
  }
  return 'desktop';
}

export function useViewport() {
  const [width, setWidth] = useState(readWidth);

  useEffect(() => {
    function handleResize() {
      setWidth(window.innerWidth);
    }

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return {
    width,
    mode: toMode(width),
    isMobile: width <= MOBILE_MAX_WIDTH,
    isTablet: width > MOBILE_MAX_WIDTH && width <= TABLET_MAX_WIDTH,
    isDesktop: width > TABLET_MAX_WIDTH,
    isCompactNav: width <= TABLET_MAX_WIDTH,
  };
}
