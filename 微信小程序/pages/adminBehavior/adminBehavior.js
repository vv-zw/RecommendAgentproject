function withPercent(items, valueKey = "value") {
  const max = Math.max(...(items || []).map((item) => Number(item[valueKey] || 0)), 0);
  return (items || []).map((item) => ({
    ...item,
    percent: max > 0 ? Math.max(8, Math.round((Number(item[valueKey] || 0) / max) * 100)) : 0,
    fillStyle: `width: ${max > 0 ? Math.max(8, Math.round((Number(item[valueKey] || 0) / max) * 100)) : 0}%;`
  }));
}

function normalizeTrendSeries(series = []) {
  return (series || []).map((group, groupIndex) => {
    const points = withPercent(group.points || [], "value").map((point, pointIndex, list) => ({
      ...point,
      isLast: pointIndex === list.length - 1,
      barStyle: `height: ${point.percent}%;`
    }));
    return {
      ...group,
      accentClass: ["warm", "ink", "alert"][groupIndex] || "warm",
      points
    };
  });
}

function normalizeTopLists(topLists = {}) {
  const listConfigs = [
    { key: "preferences", title: "偏好 Top", tone: "warm", emptyText: "暂无偏好数据" },
    { key: "watchlist", title: "待看 Top", tone: "ink", emptyText: "暂无待看数据" },
    { key: "feedback", title: "负反馈 Top", tone: "alert", emptyText: "暂无负反馈数据" }
  ];

  return listConfigs.map((config) => {
    const items = (topLists[config.key] || []).map((item, index) => ({
      ...item,
      rank: index + 1
    }));
    return {
      ...config,
      items,
      lead: items[0] || null
    };
  });
}

function buildInsight(summary) {
  const cards = summary.cards || [];
  const topGenre = (summary.genre_distribution || [])[0];
  const hotList = ((summary.top_lists || {}).watchlist || [])[0];
  const hottestCard = cards.reduce((best, item) => {
    if (!best || Number(item.value || 0) > Number(best.value || 0)) {
      return item;
    }
    return best;
  }, null);

  return {
    title: summary.headline || "用户行为分析",
    description: summary.summary_text || "从趋势、分布和高频内容观察当前用户行为。",
    badges: [
      hottestCard ? `${hottestCard.label}${hottestCard.value}` : "暂无卡片数据",
      topGenre ? `热门类型 ${topGenre.label}` : "暂无类型分布",
      hotList ? `待看焦点 ${hotList.title}` : "暂无待看热点"
    ]
  };
}

Page({
  data: {
    currentTab: "overview",
    tabOptions: [
      { key: "overview", label: "总览" },
      { key: "movie", label: "电影" },
      { key: "series", label: "剧集" }
    ],
    summary: null,
    viewModel: null,
    loading: true,
    error: ""
  },

  onLoad(options = {}) {
    const tab = String(options.tab || "overview").trim().toLowerCase();
    this.setData({
      currentTab: ["overview", "movie", "series"].includes(tab) ? tab : "overview"
    });
  },

  onShow() {
    this.fetchSummary();
  },

  getBackendUrl() {
    const app = getApp();
    return app && typeof app.getBackendUrl === "function"
      ? app.getBackendUrl()
      : "http://localhost:5000";
  },

  getAdminHeader() {
    return {
      "Content-Type": "application/json",
      "X-Admin-Token": wx.getStorageSync("adminToken") || ""
    };
  },

  handleUnauthorized() {
    wx.removeStorageSync("adminToken");
    wx.removeStorageSync("adminUsername");
    wx.redirectTo({ url: "/pages/adminLogin/adminLogin" });
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab;
    if (!tab || tab === this.data.currentTab) {
      return;
    }
    this.setData({ currentTab: tab }, () => this.fetchSummary());
  },

  buildViewModel(summary) {
    const normalizedSummary = summary || {};
    return {
      insight: buildInsight(normalizedSummary),
      trendSeries: normalizeTrendSeries((normalizedSummary.trend || {}).series || []),
      genreDistribution: withPercent(normalizedSummary.genre_distribution || [], "value"),
      topLists: normalizeTopLists(normalizedSummary.top_lists || {})
    };
  },

  fetchSummary() {
    this.setData({ loading: true, error: "" });
    wx.request({
      url: `${this.getBackendUrl()}/api/admin/behavior-summary`,
      data: { tab: this.data.currentTab },
      header: this.getAdminHeader(),
      success: (res) => {
        if (res.statusCode === 401) {
          this.handleUnauthorized();
          return;
        }

        if (res.data && res.data.code === 0) {
          const summary = res.data.data || null;
          this.setData({
            summary,
            viewModel: this.buildViewModel(summary),
            loading: false
          });
          return;
        }

        this.setData({
          loading: false,
          error: (res.data && res.data.error) || "行为分析加载失败"
        });
      },
      fail: () => {
        this.setData({
          loading: false,
          error: "网络错误，行为分析加载失败"
        });
      }
    });
  }
});
