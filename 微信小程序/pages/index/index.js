Page({
  data: {
    movieList: [],
    systemInfo: null,
    quickStats: {
      movie: 0,
      series: 0,
      watchlist: 0,
      total: 0
    },
    navigationCards: []
  },

  onLoad() {
    this.fetchSystemInfo();
    this.loadMovieList();
  },

  onShow() {
    this.loadMovieList();
  },

  getDefaultCover(item = {}) {
    const rawType = String(item.content_type || item.type || '').toLowerCase();
    const isSeries = rawType === 'series' || rawType === 'show' || item.type === '剧集';
    return isSeries
      ? 'https://via.placeholder.com/240x320/e9dccb/6f5640?text=Series'
      : 'https://via.placeholder.com/240x320/f0dfd1/8c4b3f?text=Movie';
  },

  normalizeMovieList(list = []) {
    return (list || []).map((item) => {
      const coverUrl = item.coverUrl || item.cover_url || item.image || '';
      return {
        ...item,
        name: item.name || item.title || '未命名影视',
        score: item.score || item.rating || '暂无',
        comment: item.comment || '还没有留下简介或观影感受。',
        displayCover: coverUrl || this.getDefaultCover(item)
      };
    });
  },

  buildQuickStats(list = []) {
    const stats = {
      movie: 0,
      series: 0,
      watchlist: 0,
      total: list.length
    };

    (list || []).forEach((item) => {
      const contentType = String(item.content_type || item.type || '').toLowerCase();
      if (contentType === 'movie' || item.type === '电影') {
        stats.movie += 1;
      } else if (contentType === 'series' || item.type === '剧集') {
        stats.series += 1;
      }
    });

    stats.watchlist = (wx.getStorageSync('alreadyList') || []).length;
    return stats;
  },

  buildNavigationCards(stats) {
    return [
      {
        key: 'all',
        title: '全部内容',
        subtitle: '统一查看和整理全部影视记录',
        badge: `${stats.total} 条`,
        icon: '全',
        theme: 'all',
        action: 'showAll'
      },
      {
        key: 'movie',
        title: '电影',
        subtitle: '浏览电影收藏与补充详情',
        badge: `${stats.movie} 部`,
        icon: '影',
        theme: 'movie',
        action: 'filterMovie'
      },
      {
        key: 'series',
        title: '剧集',
        subtitle: '整理剧集条目与追更内容',
        badge: `${stats.series} 部`,
        icon: '剧',
        theme: 'series',
        action: 'filterShow'
      },
      {
        key: 'watchlist',
        title: '待看清单',
        subtitle: '管理稍后想看的电影和剧集',
        badge: `${stats.watchlist} 条`,
        icon: '看',
        theme: 'watchlist',
        action: 'filterAlready'
      }
    ];
  },

  loadMovieList() {
    const list = wx.getStorageSync('totalMovieList') || [];
    const movieList = this.normalizeMovieList(list);
    const quickStats = this.buildQuickStats(movieList);
    this.setData({
      movieList,
      quickStats,
      navigationCards: this.buildNavigationCards(quickStats)
    });
  },

  fetchSystemInfo() {
    wx.request({
      url: 'http://localhost:5000/api/system-info',
      success: (res) => {
        if (res.data && res.data.code === 0) {
          this.setData({ systemInfo: res.data });
        }
      },
      fail: (err) => {
        console.error('backend_connection_failed', err);
        wx.showToast({
          title: '后端服务未启动',
          icon: 'none'
        });
      }
    });
  },

  goAdd() {
    wx.navigateTo({ url: '/pages/add/add' });
  },

  goToRecommend() {
    wx.navigateTo({ url: '/pages/recommend/recommend' });
  },

  goSetting() {
    wx.navigateTo({ url: '/pages/setting/setting' });
  },

  deleteItem(e) {
    const id = e.currentTarget.dataset.id;
    const newList = this.data.movieList.filter((item) => item.id !== id);
    this.setData({ movieList: newList });
    wx.setStorageSync('totalMovieList', newList);
    this.syncCategoryLists();
    this.loadMovieList();
    wx.showToast({ title: '已删除', icon: 'none' });
  },

  syncCategoryLists() {
    const allItems = wx.getStorageSync('totalMovieList') || [];
    const categories = {
      电影: 'movieList',
      剧集: 'showList'
    };

    Object.entries(categories).forEach(([type, key]) => {
      const filtered = allItems.filter((item) => item.type === type);
      wx.setStorageSync(key, filtered);
    });
  },

  showAll() {
    wx.navigateTo({ url: '/pages/all/all' });
  },

  filterMovie() {
    wx.navigateTo({ url: '/pages/movie/movie' });
  },

  filterShow() {
    wx.navigateTo({ url: '/pages/show/show' });
  },

  filterAlready() {
    wx.navigateTo({ url: '/pages/already/already' });
  },

  onNavCardTap(e) {
    const action = e.currentTarget.dataset.action;
    if (action && typeof this[action] === 'function') {
      this[action]();
    }
  },

  handleCoverError(e) {
    const { id } = e.currentTarget.dataset;
    const fallbackList = this.data.movieList.map((item) => (
      item.id !== id
        ? item
        : { ...item, displayCover: this.getDefaultCover(item) }
    ));

    this.setData({ movieList: fallbackList });
  }
});
