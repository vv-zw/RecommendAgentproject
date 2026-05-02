Page({
  data: {
    alreadyList: [],
    rowCount: 0,
    loading: true
  },

  onLoad() {
    this.loadAlreadyData();
  },

  onShow() {
    this.loadAlreadyData();
  },

  updateRowCount() {
    this.setData({
      rowCount: Math.ceil((this.data.alreadyList.length || 0) / 2)
    });
  },

  formatAlreadyData(data) {
    return (data || []).map((item) => {
      let selectedElements = item.selectedElements || item.genres || [];
      if (typeof selectedElements === 'string') {
        selectedElements = selectedElements.split(',').map((genre) => genre.trim()).filter(Boolean);
      }

      return {
        ...item,
        selectedElements,
        genres: selectedElements,
        coverUrl: item.coverUrl || item.cover_url || '/images/default_movie.png',
        cover_url: item.coverUrl || item.cover_url || '/images/default_movie.png',
        comment: item.comment || '暂无短评'
      };
    });
  },

  loadAlreadyData() {
    const app = getApp();
    this.setData({ loading: true });

    if (!app || typeof app.refreshWatchlistCache !== 'function') {
      const alreadyList = this.formatAlreadyData(wx.getStorageSync('alreadyList') || []);
      this.setData({ alreadyList, loading: false });
      this.updateRowCount();
      return;
    }

    app.refreshWatchlistCache().then(() => {
      const alreadyList = this.formatAlreadyData(wx.getStorageSync('alreadyList') || []);
      this.setData({ alreadyList, loading: false });
      this.updateRowCount();
    }).catch((error) => {
      console.error('load_watchlist_failed', error);
      const alreadyList = this.formatAlreadyData(wx.getStorageSync('alreadyList') || []);
      this.setData({ alreadyList, loading: false });
      this.updateRowCount();
      wx.showToast({ title: '待看列表加载失败', icon: 'none' });
    });
  },

  deleteAlready(e) {
    const id = e.currentTarget.dataset.id;
    const item = this.data.alreadyList.find((entry) => entry.id === id);

    wx.showModal({
      title: '删除确认',
      content: '确定要从待看列表中删除吗？',
      success: (res) => {
        if (!res.confirm) {
          return;
        }

        const app = getApp();
        if (!app || typeof app.removeWatchlistItem !== 'function') {
          wx.showToast({ title: '当前版本暂不支持同步删除', icon: 'none' });
          return;
        }

        app.removeWatchlistItem(id, item?.content_type || item?.type || '').then(() => {
          this.loadAlreadyData();
          wx.showToast({ title: '删除成功', icon: 'none' });
        }).catch((error) => {
          console.error('remove_watchlist_failed', error);
          wx.showToast({ title: '删除失败，请重试', icon: 'none' });
        });
      }
    });
  },

  onPullDownRefresh() {
    this.loadAlreadyData();
    wx.stopPullDownRefresh();
  }
});
