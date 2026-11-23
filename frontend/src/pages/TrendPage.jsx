import { NewsSnsView } from '../components/NewsSnsView';
import StoredNewsView from '../components/StoredNewsView';
export default function TrendPage() {
  return <div className="space-y-8">
    <StoredNewsView />
    <details className="rounded-xl border border-amber-200 bg-amber-50 p-4">
      <summary className="cursor-pointer font-medium">분석 화면 미리보기 · 가상 데이터</summary>
      <p className="my-4 text-sm text-amber-900">아래 순위·감성·SNS 반응은 데모입니다. 위의 실제 기사와 연결된 분석 결과가 아닙니다.</p>
      <NewsSnsView />
    </details>
  </div>;
}
