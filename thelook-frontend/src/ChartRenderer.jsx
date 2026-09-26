import { useEffect, useRef } from "react";
import {
  Chart,
  BarController,
  LineController,
  PieController,
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
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend
);

// config shape matches app/tools/chart_tool.py's build_chart_config output:
// { type: "bar" | "line" | "pie", labels: [...], datasets: [{ label, data, backgroundColor }] }
export default function ChartRenderer({ config }) {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!canvasRef.current || !config) return;

    chartRef.current?.destroy();
    chartRef.current = new Chart(canvasRef.current, {
      type: config.type || "bar",
      data: {
        labels: config.labels,
        datasets: config.datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: "#c7ccda" } },
        },
        scales:
          config.type === "pie"
            ? {}
            : {
                x: { ticks: { color: "#8b92a5" }, grid: { color: "#262b36" } },
                y: { ticks: { color: "#8b92a5" }, grid: { color: "#262b36" } },
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
