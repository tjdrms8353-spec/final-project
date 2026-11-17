// Preserve existing HTML and scripts until each page is migrated to React.
export default function LegacyPage({ page, title }) {
  return <iframe src={`/legacy/${page}.html`} title={title} className="block h-[calc(100dvh-64px)] w-full border-0" />;
}
