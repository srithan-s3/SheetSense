import { useState } from "react";
import { BarChart3 } from "lucide-react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  ScatterChart,
  Scatter,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";
import type { Chart, ChartType } from "../types";
import { chartLabels, compact } from "../utils/format";
import { EmptyState } from "./UI";
const colors = [
  "#6255de",
  "#23a89b",
  "#8c82f0",
  "#f1ad5d",
  "#4b88d3",
  "#c67ca6",
  "#8caa62",
  "#b4aeea",
];
const tooltipStyle = {
  background: "var(--surface)",
  border: "1px solid var(--border)",
  borderRadius: 12,
  color: "var(--text)",
  fontSize: 12,
  boxShadow: "0 8px 24px #00000010",
};
export function ChartCard({
  chart,
  compactView = false,
}: {
  chart: Chart;
  compactView?: boolean;
}) {
  const [selected, setSelected] = useState<ChartType>(chart.type);
  const available = [
    ...new Set([
      chart.type,
      ...chart.alternatives.filter((type) => type in chartLabels),
    ]),
  ] as ChartType[];
  const type = available.includes(selected) ? selected : chart.type;
  const y = chart.y_keys[0];
  const grid = (
    <CartesianGrid
      strokeDasharray="3 5"
      stroke="var(--border)"
      vertical={false}
    />
  );
  const xAxis = (
    <XAxis
      dataKey={chart.x_key}
      tick={{ fill: "var(--muted)", fontSize: 11 }}
      tickLine={false}
      axisLine={false}
      tickMargin={12}
      minTickGap={16}
      tickFormatter={(value) =>
        String(value).length > 15
          ? `${String(value).slice(0, 14)}…`
          : String(value)
      }
    />
  );
  const yAxis = (
    <YAxis
      tickFormatter={compact}
      tick={{ fill: "var(--muted)", fontSize: 11 }}
      tickLine={false}
      axisLine={false}
      width={54}
    />
  );
  const tip = (
    <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--hover)" }} />
  );
  let content;
  if (type === "pie" || type === "doughnut")
    content = (
      <PieChart>
        <Pie
          data={chart.data}
          nameKey={chart.x_key}
          dataKey={y}
          innerRadius={type === "doughnut" ? "58%" : 0}
          outerRadius="83%"
          paddingAngle={chart.data.length > 1 ? 3 : 0}
          stroke="none"
        >
          {chart.data.map((_, index) => (
            <Cell key={index} fill={colors[index % colors.length]} />
          ))}
        </Pie>
        {tip}
        <Legend
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: 11, paddingTop: 12 }}
        />
      </PieChart>
    );
  else if (type === "scatter")
    content = (
      <ScatterChart margin={{ top: 12, right: 12, bottom: 12, left: 0 }}>
        {grid}
        <XAxis
          type="number"
          dataKey={chart.x_key}
          name={chart.x_label}
          tickFormatter={compact}
          tick={{ fill: "var(--muted)", fontSize: 11 }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          type="number"
          dataKey={y}
          name={chart.y_label}
          tickFormatter={compact}
          tick={{ fill: "var(--muted)", fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={54}
        />
        <Tooltip
          contentStyle={tooltipStyle}
          cursor={{ strokeDasharray: "3 3" }}
        />
        <Scatter
          name={chart.y_label}
          data={chart.data}
          fill={colors[0]}
          fillOpacity={0.7}
        />
      </ScatterChart>
    );
  else if (type === "line")
    content = (
      <LineChart
        data={chart.data}
        margin={{ top: 12, right: 18, bottom: 12, left: 0 }}
      >
        {grid}
        {xAxis}
        {yAxis}
        {tip}
        {chart.y_keys.map((key, index) => (
          <Line
            key={key}
            name={chart.series_labels?.[key] || key}
            type="monotone"
            dataKey={key}
            stroke={colors[index % colors.length]}
            strokeWidth={2.5}
            dot={chart.data.length < 15 ? { r: 3 } : false}
            activeDot={{ r: 5 }}
            connectNulls={false}
          />
        ))}
        {chart.y_keys.length > 1 && (
          <Legend
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: 11 }}
          />
        )}
      </LineChart>
    );
  else if (type === "horizontal_bar")
    content = (
      <BarChart
        data={chart.data}
        layout="vertical"
        margin={{ top: 10, right: 20, bottom: 8, left: 0 }}
      >
        <CartesianGrid
          strokeDasharray="3 5"
          stroke="var(--border)"
          horizontal={false}
        />
        <XAxis
          type="number"
          tickFormatter={compact}
          tick={{ fill: "var(--muted)", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey={chart.x_key}
          tick={{ fill: "var(--muted)", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={95}
          tickFormatter={(value) => String(value).slice(0, 14)}
        />
        {tip}
        {chart.y_keys.map((key, index) => (
          <Bar
            key={key}
            name={chart.series_labels?.[key] || key}
            dataKey={key}
            fill={colors[index % colors.length]}
            radius={[0, 4, 4, 0]}
            maxBarSize={26}
          />
        ))}
      </BarChart>
    );
  else
    content = (
      <BarChart
        data={chart.data}
        margin={{ top: 12, right: 12, bottom: 12, left: 0 }}
        barCategoryGap={type === "histogram" ? "8%" : "28%"}
      >
        {grid}
        {xAxis}
        {yAxis}
        {tip}
        {chart.y_keys.map((key, index) => (
          <Bar
            key={key}
            name={chart.series_labels?.[key] || key}
            dataKey={key}
            stackId={type === "stacked_bar" ? "total" : undefined}
            fill={colors[index % colors.length]}
            radius={[4, 4, 0, 0]}
            maxBarSize={44}
          />
        ))}
        {chart.y_keys.length > 1 && (
          <Legend
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: 11 }}
          />
        )}
      </BarChart>
    );
  return (
    <article className={`chart-card ${compactView ? "chart-compact" : ""}`}>
      <div className="chart-heading">
        <div>
          <h3>{chart.title}</h3>
          <p>{chart.description}</p>
        </div>
        {available.length > 1 && !compactView && (
          <select
            className="chart-select"
            aria-label={`Chart type for ${chart.title}`}
            value={type}
            onChange={(event) => setSelected(event.target.value as ChartType)}
          >
            {[...new Set(available)].map((item) => (
              <option key={item} value={item}>
                {chartLabels[item]}
              </option>
            ))}
          </select>
        )}
      </div>
      {chart.data.length ? (
        <>
          <div
            className="chart-canvas"
            role="img"
            aria-label={`${chart.title}. ${chart.description}. ${chart.data.length} data points.`}
          >
            <ResponsiveContainer width="100%" height="100%" minWidth={0}>
              {content}
            </ResponsiveContainer>
          </div>
          {type !== "pie" && type !== "doughnut" && (
            <div className="axis-caption">
              <span>{chart.y_label}</span>
              <span>{chart.x_label}</span>
            </div>
          )}
        </>
      ) : (
        <EmptyState icon={<BarChart3 size={24} />} title="No chart data">
          Try adjusting your filters to include more records.
        </EmptyState>
      )}
    </article>
  );
}
