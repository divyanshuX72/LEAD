import { Link2 } from 'lucide-react';
import { getDomain } from '@/utils/utils';

interface WebsiteLinkProps {
  url: string;
}

export function WebsiteLink({ url }: WebsiteLinkProps) {
  if (!url) return null;

  const displayUrl = getDomain(url);
  const href = url.startsWith('http') ? url : `https://${url}`;

  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      title={url}
      className="flex items-center gap-1.5 text-[11.5px] text-slate-500 hover:text-blue-600 hover:underline mt-1.5 w-fit max-w-[200px] lg:max-w-[250px]"
    >
      <Link2 className="h-3 w-3 shrink-0" />
      <span className="truncate">{displayUrl}</span>
    </a>
  );
}
