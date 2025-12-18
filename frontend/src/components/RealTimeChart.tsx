import { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';

interface DataPoint {
  time: string;
  value: number;
}

interface RealTimeChartProps {
  data: DataPoint[];
  color?: string;
  height?: number;
  title?: string;
  type?: 'line' | 'area';
  yAxisLabel?: string;
}

export default function RealTimeChart({
  data,
  color = '#3b82f6',
  height = 200,
  title,
  type = 'area',
  yAxisLabel,
}: RealTimeChartProps) {
  const ChartComponent = type === 'area' ? AreaChart : LineChart;

  return (
    <div>
      {title && (
        <h3 className="text-sm font-medium text-gray-400 mb-4">{title}</h3>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <ChartComponent
          data={data}
          margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
        >
          <defs>
            <linearGradient id={`gradient-${color}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
          <XAxis
            dataKey="time"
            stroke="#6b7280"
            fontSize={12}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke="#6b7280"
            fontSize={12}
            tickLine={false}
            axisLine={false}
            label={
              yAxisLabel
                ? { value: yAxisLabel, angle: -90, position: 'insideLeft', fill: '#6b7280' }
                : undefined
            }
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1f2937',
              border: '1px solid #374151',
              borderRadius: '8px',
              color: '#f3f4f6',
            }}
            labelStyle={{ color: '#9ca3af' }}
          />
          {type === 'area' ? (
            <Area
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              fill={`url(#gradient-${color})`}
            />
          ) : (
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: color }}
            />
          )}
        </ChartComponent>
      </ResponsiveContainer>
    </div>
  );
}

// Hook to manage real-time chart data
export function useChartData(maxPoints: number = 60) {
  const [data, setData] = useState<DataPoint[]>([]);

  const addDataPoint = (value: number) => {
    const now = new Date();
    const time = now.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });

    setData((prev) => {
      const newData = [...prev, { time, value }];
      if (newData.length > maxPoints) {
        return newData.slice(-maxPoints);
      }
      return newData;
    });
  };

  const reset = () => setData([]);

  return { data, addDataPoint, reset };
}
