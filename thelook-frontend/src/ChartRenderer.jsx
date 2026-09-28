import { useEffect, useRef } from "react";
import {
  Chart,
  BarController,
  LineController,
  PieController,
  DoughnutController,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
} from "chart.js";

Chart.register(
  BarController,
  LineController,
  PieController,
  DoughnutController,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend
);

const FALLBACK_PALETTE = [
  "#6366F1", "#06B6D4", "#10B981", "#F59E0B", "#EC4899",
  "#8B5CF6", "#3B82F6", "#14B8A6", "#F97316", "#E11D48"
];

export default function ChartRenderer({ config }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !config) return;

    chartRef.current?.destroy();

    const chartType = config.type || "bar";
    const isPieOrDoughnut = chartType === "pie" || chartType === "doughnut";

    // Ensure multi-color datasets for pie/doughnut even if old config has a single color string
    const processedDatasets = (config.datasets || []).map((ds) => {
      let bg = ds.backgroundColor;
      if (isPieOrDoughnut && (!Array.isArray(bg) || bg.length <= 1)) {
        bg = (config.labels || []).map((_, idx) => FALLBACK_PALETTE[idx % FALLBACK_PALETTE.length]);
      }
      return {
        ...ds,
        backgroundColor: bg,
        borderColor: isPieOrDoughnut ? "#181b22" : ds.borderColor,
        borderWidth: isPieOrDoughnut ? 2 : ds.borderWidth ?? 1,
      };
    });

    chartRef.current = new Chart(canvasRef.current, {
      type: chartType,
      data: {
        labels: config.labels,
        datasets: processedDatasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: isPieOrDoughnut || processedDatasets.length > 1,
            position: isPieOrDoughnut ? "bottom" : "top",
            labels: {
              color: "#c7ccda",
              boxWidth: 14,
              padding: 12,
              font: { size: 12 },
            },
          },
          tooltip: {
            backgroundColor: "#1e222b",
            titleColor: "#f3f4f6",
            bodyColor: "#c7ccda",
            borderColor: "#374151",
            borderWidth: 1,
            padding: 10,
          },
        },
        scales: isPieOrDoughnut
          ? {}
          : {
              x: {
                ticks: { color: "#8b92a5", maxRotation: 45, minRotation: 0 },
                grid: { color: "rgba(255, 255, 255, 0.05)" },
              },
              y: {
                ticks: { color: "#8b92a5" },
                grid: { color: "rgba(255, 255, 255, 0.05)" },
              },
            },
      },
    });

    return () => chartRef.current?.destroy();
  }, [config]);

  return (
    <div className="chart-box">
      <canvas ref={canvasRef} height="280" />
    </div>
  );
}
