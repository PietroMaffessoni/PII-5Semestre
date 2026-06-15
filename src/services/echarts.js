import { init, use } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

let isRegistered = false

export function getEcharts() {
  if (!isRegistered) {
    use([
      BarChart,
      LineChart,
      GridComponent,
      TooltipComponent,
      LegendComponent,
      CanvasRenderer,
    ])
    isRegistered = true
  }

  return { init }
}
