Page({
  data: {
    gridList: [],
    loading: false,
    error: '',
    countWeights: {},
    recommendReasons: [],
    syncStatus: '',
    searchQuery: '',
    searchResults: [],
    showSearch: false,
    activeTab: 'recommend',
    alreadyList: []
  },

  onLoad() {
    this.fetchRecommendations();
    this.loadAlreadyData();
  },

  onShow() {
    this.loadAlreadyData();
  },

  getBackendUrl() {
    const app = getApp();
    return app && typeof app.getBackendUrl === 'function'
      ? app.getBackendUrl()
      : 'http://localhost:5000';
  },

  normalizeGenres(item) {
    const rawGenres = item?.genres ?? item?.selectedElements ?? [];
    if (Array.isArray(rawGenres)) {
      return rawGenres.map((genre) => String(genre).trim()).filter(Boolean);
    }
    if (typeof rawGenres === 'string') {
      return rawGenres
        .split(/[,/|、，]/)
        .map((genre) => genre.trim())
        .filter(Boolean);
    }
    return [];
  },

  normalizeSeriesItem(series = {}, index = 0) {
    const genres = this.normalizeGenres(series);
    const rating = typeof series.rating === 'number' ? series.rating.toFixed(1) : (series.rating || '暂无评分');
    const coverUrl = series.cover_url || series.coverUrl || '/images/default_series.png';

    return {
      ...series,
      id: series.id || series.seriesId || `series_${Date.now()}_${index}`,
      title: series.title || series.name || '未命名剧集',
      name: series.name || series.title || '未命名剧集',
      rating,
      cover_url: coverUrl,
      coverUrl,
      genres,
      selectedElements: genres,
      genresText: genres.length ? genres.join(' / ') : '未知',
      recommendMatchScore: this.formatMatchScore(series.recommend_match_score, series.final_score),
      type: 'series',
      content_type: 'series'
    };
  },

  formatMatchScore(recommendMatchScore, finalScore) {
    let score = Number(recommendMatchScore);
    if (!Number.isFinite(score)) {
      score = Math.round(Number(finalScore || 0) * 100);
    }
    if (!Number.isFinite(score)) {
      return 'N/A';
    }
    return `${Math.max(0, Math.min(100, Math.round(score)))}%`;
  },

  formatToGrid(list) {
    const grid = [];
    for (let i = 0; i < list.length; i += 3) {
      grid.push(list.slice(i, i + 3));
    }
    return grid;
  },

  formatRecommendReasons(recommendReasons) {
    if (Array.isArray(recommendReasons) && recommendReasons.length) {
      return recommendReasons.map((item) => String(item || '').trim()).filter(Boolean).slice(0, 5);
    }
    return [];
  },

  loadAlreadyData() {
    const alreadyList = (wx.getStorageSync('alreadyList') || []).map((item, index) => this.normalizeSeriesItem(item, index));
    this.setData({ alreadyList });
  },

  switchTab(e) {
    const tab = e.currentTarget.dataset.tab;
    this.setData({
      activeTab: tab,
      showSearch: tab === 'search',
      error: ''
    });
  },

  processRecommendData(recommendList, countWeights, recommendReasons) {
    const formattedList = (Array.isArray(recommendList) ? recommendList : []).map((item, index) => this.normalizeSeriesItem(item, index));
    this.setData({
      gridList: this.formatToGrid(formattedList),
      countWeights: countWeights || {},
      recommendReasons: this.formatRecommendReasons(recommendReasons),
      loading: false,
      error: formattedList.length ? '' : '暂时没有推荐内容。'
    });
  },

  fetchRecommendations() {
    this.setData({ loading: true, error: '' });
    wx.request({
      url: `${this.getBackendUrl()}/get_recommend`,
      data: { type: 'series' },
      timeout: 10000,
      success: (res) => {
        if (res.data && res.data.code === 0) {
          this.processRecommendData(
            res.data.data,
            res.data.count_weights,
            res.data.recommend_reasons_summary
          );
          return;
        }

        this.setData({
          loading: false,
          error: (res.data && res.data.error) || '加载推荐失败'
        });
      },
      fail: () => {
        this.setData({
          loading: false,
          error: '加载推荐失败'
        });
      }
    });
  },

  refreshRecommendations() {
    const app = getApp();
    if (!app || typeof app.syncAndRefresh !== 'function') {
      this.fetchRecommendations();
      return;
    }

    this.setData({
      syncStatus: '刷新中...',
      loading: true,
      error: ''
    });

    app.syncAndRefresh('series', {
      silent: true,
      onSuccess: () => {
        this.setData({ syncStatus: '已更新' });
        this.fetchRecommendations();
        setTimeout(() => this.setData({ syncStatus: '' }), 2500);
      },
      onFail: () => {
        this.setData({
          syncStatus: '刷新失败',
          loading: false
        });
        setTimeout(() => this.setData({ syncStatus: '' }), 2500);
      }
    });
  },

  onImageError(e) {
    const seriesId = e.currentTarget.dataset.id;
    const updatePoster = (list) => list.map((item) => (
      item.id === seriesId
        ? { ...item, cover_url: '/images/default_series.png', coverUrl: '/images/default_series.png' }
        : item
    ));

    this.setData({
      gridList: this.data.gridList.map((row) => updatePoster(row)),
      searchResults: updatePoster(this.data.searchResults),
      alreadyList: updatePoster(this.data.alreadyList)
    });
  },

  goToDetail(e) {
    const id = e.currentTarget.dataset.id;
    wx.navigateTo({ url: `/pages/show/show?id=${id}` });
  },

  getSeriesById(id) {
    for (const row of this.data.gridList) {
      const series = row.find((item) => item.id === id);
      if (series) {
        return series;
      }
    }
    return this.data.searchResults.find((item) => item.id === id)
      || this.data.alreadyList.find((item) => item.id === id)
      || null;
  },

  handleNegativeFeedback(e) {
    const seriesId = e.currentTarget.dataset.id;
    const series = this.getSeriesById(seriesId);
    if (!series) {
      return;
    }

    wx.showModal({
      title: '减少此类推荐',
      content: `要减少与“${series.title}”相似的推荐吗？`,
      success: (res) => {
        if (!res.confirm) {
          return;
        }

        wx.request({
          url: `${this.getBackendUrl()}/negative-feedback`,
          method: 'POST',
          data: {
            item_id: seriesId,
            type: 'series',
            reason: 'user_not_interested'
          }
        });

        const gridList = this.data.gridList
          .map((row) => row.filter((item) => item.id !== seriesId))
          .filter((row) => row.length > 0);
        this.setData({ gridList });
        wx.showToast({ title: '已记录', icon: 'success' });
      }
    });
  },

  addToWatchlist(e) {
    const seriesId = e.currentTarget.dataset.id;
    const series = this.getSeriesById(seriesId);
    if (!series) {
      wx.showToast({ title: '未找到该剧集', icon: 'none' });
      return;
    }

    const app = getApp();
    if (!app || typeof app.addWatchlistItem !== 'function') {
      wx.showToast({ title: '待看功能暂不可用', icon: 'none' });
      return;
    }

    app.addWatchlistItem({
      ...series,
      type: 'series',
      content_type: 'series'
    }).then(() => {
      this.loadAlreadyData();
      wx.showToast({ title: '已加入待看', icon: 'success' });
    }).catch(() => {
      wx.showToast({ title: '加入待看失败', icon: 'none' });
    });
  },

  deleteAlready(e) {
    const id = e.currentTarget.dataset.id;
    const app = getApp();
    if (!app || typeof app.removeWatchlistItem !== 'function') {
      wx.showToast({ title: '待看功能暂不可用', icon: 'none' });
      return;
    }

    app.removeWatchlistItem(id, 'series')
      .then(() => {
        this.loadAlreadyData();
        wx.showToast({ title: '移除成功', icon: 'none' });
      })
      .catch(() => {
        wx.showToast({ title: '移除失败', icon: 'none' });
      });
  },

  searchSeries(e) {
    const rawQuery = e && e.detail && typeof e.detail.value === 'string'
      ? e.detail.value
      : this.data.searchQuery;
    const query = String(rawQuery || '').trim();
    if (!query) {
      this.setData({ searchResults: [], showSearch: false, error: '' });
      return;
    }

    this.setData({ searchQuery: query, loading: true, error: '', showSearch: true });
    wx.request({
      url: `${this.getBackendUrl()}/search`,
      data: { q: query, type: 'series' },
      success: (res) => {
        if (res.data && res.data.code === 0) {
          const results = (res.data.results || []).map((item, index) => this.normalizeSeriesItem(item, index));
          this.setData({
            searchResults: results,
            showSearch: true,
            loading: false,
            error: ''
          });
          return;
        }

        this.setData({
          loading: false,
          searchResults: [],
          showSearch: true,
          error: (res.data && res.data.error) || '搜索失败'
        });
      },
      fail: () => {
        this.setData({
          loading: false,
          searchResults: [],
          showSearch: true,
          error: '搜索失败'
        });
      }
    });
  },

  onSearchInput(e) {
    this.setData({ searchQuery: e.detail.value });
  },

  clearSearch() {
    this.setData({ searchQuery: '', searchResults: [], showSearch: false, error: '' });
  },

  goToAddSeries() {
    wx.navigateTo({ url: '/pages/add/add' });
  }
});
