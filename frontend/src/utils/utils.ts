import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function getDomain(url: string): string {
  if (!url) return '';
  try {
    const urlString = url.startsWith('http') ? url : `https://${url}`;
    const urlObj = new URL(urlString);
    return urlObj.hostname.replace(/^www\./, '');
  } catch (e) {
    return url.length > 40 ? url.substring(0, 40) + '...' : url;
  }
}
