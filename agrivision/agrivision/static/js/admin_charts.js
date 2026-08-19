// AgriVision Admin Dashboard Analytics Chart Initializer

document.addEventListener("DOMContentLoaded", function () {
  // 1. Sales Trend Line Chart
  const salesCtx = document.getElementById("salesTrendChart");
  if (salesCtx && window.chartData) {
    new Chart(salesCtx, {
      type: "line",
      data: {
        labels: window.chartData.salesMonths || ["Sep", "Oct", "Nov", "Dec", "Jan", "Feb"],
        datasets: [
          {
            label: "Revenue (₹)",
            data: window.chartData.salesTrend || [12500, 18400, 24600, 31200, 28900, 35400],
            borderColor: "#10b981",
            backgroundColor: "rgba(16, 185, 129, 0.12)",
            borderWidth: 3,
            fill: true,
            tension: 0.4,
            pointBackgroundColor: "#10b981",
            pointBorderColor: "#ffffff",
            pointBorderWidth: 2,
            pointRadius: 5,
            pointHoverRadius: 7,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (context) {
                return " ₹" + Number(context.raw).toLocaleString("en-IN");
              },
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: "#f1f5f9" },
            ticks: {
              callback: function (value) {
                return "₹" + value.toLocaleString("en-IN");
              },
            },
          },
          x: {
            grid: { display: false },
          },
        },
      },
    });
  }

  // 2. Order Status Doughnut Chart
  const orderCtx = document.getElementById("orderStatusChart");
  if (orderCtx && window.chartData) {
    const orderData = window.chartData.orderStatus || {
      Pending: 3,
      Confirmed: 2,
      Processing: 4,
      Shipped: 6,
      Delivered: 12,
      Cancelled: 1,
    };
    new Chart(orderCtx, {
      type: "doughnut",
      data: {
        labels: Object.keys(orderData),
        datasets: [
          {
            data: Object.values(orderData),
            backgroundColor: [
              "#f59e0b", // Pending - amber
              "#3b82f6", // Confirmed - blue
              "#6366f1", // Processing - indigo
              "#06b6d4", // Shipped - cyan
              "#10b981", // Delivered - emerald
              "#ef4444", // Cancelled - rose
            ],
            borderWidth: 2,
            borderColor: "#ffffff",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "70%",
        plugins: {
          legend: {
            position: "bottom",
            labels: { boxWidth: 12, padding: 12, font: { size: 11 } },
          },
        },
      },
    });
  }

  // 3. Top Products Bar Chart
  const topProdCtx = document.getElementById("topProductsChart");
  if (topProdCtx && window.chartData) {
    new Chart(topProdCtx, {
      type: "bar",
      data: {
        labels: window.chartData.topProdLabels || [],
        datasets: [
          {
            label: "Units Sold",
            data: window.chartData.topProdData || [],
            backgroundColor: "rgba(16, 185, 129, 0.85)",
            borderRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: "y",
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: {
            beginAtZero: true,
            grid: { color: "#f1f5f9" },
          },
          y: {
            grid: { display: false },
          },
        },
      },
    });
  }

  // 4. Provider Requests Status Doughnut Chart
  const reqCtx = document.getElementById("requestStatusChart");
  if (reqCtx && window.chartData) {
    const reqData = window.chartData.requestStatus || { Pending: 3, Approved: 8, Rejected: 2 };
    new Chart(reqCtx, {
      type: "doughnut",
      data: {
        labels: Object.keys(reqData),
        datasets: [
          {
            data: Object.values(reqData),
            backgroundColor: ["#f59e0b", "#10b981", "#ef4444"],
            borderWidth: 2,
            borderColor: "#ffffff",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "65%",
        plugins: {
          legend: { position: "bottom" },
        },
      },
    });
  }
});
