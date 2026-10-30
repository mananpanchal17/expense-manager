// Fetch JSON rather than inserting user-controlled text into executable scripts.
(async () => {
  const charts = [];
  const palette = ['#147d64','#769ee4','#e5b077','#b78cc6','#e2858d','#64b5bf','#a4b677'];
  try {
    if (typeof Chart === 'undefined') throw new Error('Chart library unavailable');
    const response = await fetch('/reports/chart-data', {headers: {'Accept':'application/json'}});
    if (!response.ok) throw new Error('Chart data unavailable');
    const data = await response.json();
    const money = new Intl.NumberFormat(undefined, {style:'currency',currency:data.currency});
    const options = () => ({responsive:true, maintainAspectRatio:false,
      plugins:{legend:{position:'bottom'},tooltip:{callbacks:{label:ctx => `${ctx.dataset.label || ctx.label}: ${money.format(typeof ctx.parsed === 'number' ? ctx.parsed : ctx.parsed.y)}`}}}});
    charts.push(new Chart(document.getElementById('category-chart'), {
      type:'pie', data:{labels:data.category_labels,datasets:[{data:data.category_values,backgroundColor:palette,borderWidth:2}]}, options:options()
    }));
    if (!data.category_values.length) document.getElementById('category-empty').classList.remove('d-none');
    charts.push(new Chart(document.getElementById('trend-chart'), {
      type:'line', data:{labels:data.labels,datasets:[{label:'Expenses',data:data.expense,borderColor:'#147d64',backgroundColor:'rgba(20,125,100,0.12)',fill:true,tension:.3}]},
      options:{...options(),scales:{y:{beginAtZero:true}}}
    }));
    charts.push(new Chart(document.getElementById('comparison-chart'), {
      type:'bar', data:{labels:data.labels,datasets:[{label:'Income',data:data.income,backgroundColor:'#147d64',borderRadius:4},{label:'Expenses',data:data.expense,backgroundColor:'#e5b077',borderRadius:4}]},
      options:{...options(),scales:{y:{beginAtZero:true}}}
    }));
    function recolor() {
      const color = document.documentElement.dataset.bsTheme === 'dark' ? '#cbd5e1' : '#536472';
      charts.forEach(chart => {
        chart.options.plugins.legend.labels = {color};
        if (chart.config.type !== 'pie') {
          for (const axis of ['x','y']) {
            chart.options.scales[axis] = {...chart.options.scales[axis],ticks:{color},grid:{color:'rgba(128,128,128,.12)'}};
          }
        }
        chart.update();
      });
    }
    recolor(); window.addEventListener('themechange', recolor);
  } catch (_) { document.getElementById('chart-error').classList.remove('d-none'); }
})();
