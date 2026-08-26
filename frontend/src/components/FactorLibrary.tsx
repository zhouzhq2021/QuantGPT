import { useState, useEffect, useCallback } from "react";
import { Star, Trash2, ExternalLink, ChevronDown, ChevronUp } from "lucide-react";
import { useColorMode } from "../contexts/ColorModeContext";
import type { SavedFactor } from "../api/factorLibrary";
import { fetchFactors, deleteFactor } from "../api/factorLibrary";
import { getReportUrl } from "../api/client";

function pct(n: number): string {
  return (n * 100).toFixed(1) + "%";
}

function FactorItem({
  factor,
  onDelete,
}: {
  factor: SavedFactor;
  onDelete: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const m = factor.metrics;
  const bs = factor.backtest_summary as Record<string, number> | null;
  const { isDark, positiveClass, negativeClass } = useColorMode();

  return (
    <div className={`group rounded-lg border border-gray-150 ${isDark ? "bg-gray-900" : "bg-white"} px-3 py-2.5 hover:shadow-sm transition-shadow`}>
      {/* Expression — single line truncated */}
      <div className="flex items-center gap-2 min-w-0">
        <button type="button" onClick={() => setExpanded((v) => !v)} className="flex min-w-0 flex-1 items-center gap-2 text-left">
        <code className={`text-xs ${isDark ? "text-amber-400" : "text-blue-700"} font-mono truncate flex-1`} title={factor.expression}>
          {factor.expression}
        </code>
        {expanded ? <ChevronUp className="h-3.5 w-3.5 shrink-0 text-gray-400" /> : <ChevronDown className="h-3.5 w-3.5 shrink-0 text-gray-400" />}
        </button>
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
          {factor.report_url && (
            <a
              href={getReportUrl(factor.report_url)}
              target="_blank"
              rel="noreferrer"
              className="p-1 rounded text-gray-400 hover:text-blue-600"
              title="查看报告"
            >
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
          <button
            onClick={(e) => { e.stopPropagation(); if (confirm("确定删除？")) onDelete(factor.id); }}
            className="p-1 rounded text-gray-400 hover:text-red-500"
            title="删除"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </div>
      </div>

      {/* Compact metrics row */}
      {m && (
        <div className={`flex items-center gap-2 mt-1.5 text-[11px] ${isDark ? "text-gray-400" : "text-gray-500"}`}>
          <span>S <span className={`${isDark ? "text-gray-300" : "text-gray-700"} font-medium`}>{m.sharpe.toFixed(2)}</span></span>
          <span className="text-gray-200">|</span>
          <span className={m.cagr >= 0 ? positiveClass : negativeClass}>{pct(m.cagr)}</span>
          <span className="text-gray-200">|</span>
          <span className={negativeClass}>{pct(m.max_drawdown)}</span>
          {bs && (
            <>
              <span className="text-gray-200">|</span>
              <span>M {(bs.monotonicity_score ?? 0).toFixed(1)}</span>
            </>
          )}
        </div>
      )}

      {/* Meta line */}
      {factor.interpretation && (
        <div className={`mt-2 rounded-md px-2 py-1.5 text-[11px] ${isDark ? "bg-gray-800 text-gray-300" : "bg-blue-50 text-gray-600"}`}>
          <span className="font-medium">AI Analysis：</span>
          {String(factor.interpretation.conclusion || factor.interpretation.logic || "")}
        </div>
      )}
      {expanded && factor.interpretation && (
        <div className={`mt-2 space-y-1.5 rounded-md border px-2.5 py-2 text-[11px] ${isDark ? "border-gray-700 bg-gray-800/70 text-gray-300" : "border-blue-100 bg-blue-50/50 text-gray-600"}`}>
          {(["logic", "source", "guidance", "risk", "conclusion"] as const).map((key) => factor.interpretation?.[key] ? (
            <p key={key}><span className="font-medium">{({logic:"因子逻辑", source:"收益来源", guidance:"交易指导", risk:"失效风险", conclusion:"核心结论"} as Record<string,string>)[key]}：</span>{String(factor.interpretation[key])}</p>
          ) : null)}
          {Array.isArray(factor.interpretation.suggestions) && factor.interpretation.suggestions.length > 0 && (
            <p><span className="font-medium">改进建议：</span>{factor.interpretation.suggestions.map(String).join("；")}</p>
          )}
          {factor.report_url && (
            <a href={getReportUrl(factor.report_url)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 pt-1 text-blue-600 hover:underline">
              <ExternalLink className="h-3 w-3" /> 打开完整回测报告
            </a>
          )}
        </div>
      )}
      <div className="flex items-center gap-2 mt-1 text-[10px] text-gray-400">
        {factor.params && (
          <span>{(factor.params as Record<string, string>).universe}</span>
        )}
        {factor.created_at && (
          <span>{new Date(factor.created_at).toLocaleDateString("zh-CN")}</span>
        )}
      </div>
    </div>
  );
}

export default function FactorLibrary() {
  const { isDark } = useColorMode();
  const [factors, setFactors] = useState<SavedFactor[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchFactors();
      setFactors(data);
    } catch (e) {
      console.error("Failed to load factors:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id: string) => {
    try {
      await deleteFactor(id);
      setFactors((prev) => prev.filter((f) => f.id !== id));
    } catch (e) {
      alert("删除失败: " + (e instanceof Error ? e.message : "未知错误"));
    }
  };

  if (loading) {
    return <div className="text-center py-8 text-xs text-gray-400">加载中...</div>;
  }

  if (factors.length === 0) {
    return (
      <div className="text-center py-12">
        <Star className="h-8 w-8 text-gray-200 mx-auto mb-2" />
        <p className={`text-xs ${isDark ? "text-gray-400" : "text-gray-500"}`}>因子库为空</p>
        <p className="text-[10px] text-gray-400 mt-1">回测结果页点击「收藏」保存因子</p>
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      <p className="text-xs text-gray-400 px-1">{factors.length} 个因子</p>
      {factors.map((f) => (
        <FactorItem key={f.id} factor={f} onDelete={handleDelete} />
      ))}
    </div>
  );
}
