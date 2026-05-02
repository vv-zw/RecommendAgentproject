Page({
  data: {
    items: [],
    page: 1,
    pages: 1,
    total: 0,
    keyword: '',
    contentType: '',
    typeOptions: ['全部', '电影', '剧集'],
    typeIndex: 0,
    loading: true,
    error: ''
  },

  onLoad() {
    this.fetchContent();
  },

  getBackendUrl() {
    const app = getApp();
    return (app && typeof app.getBackendUrl === 'function')
      ? app.getBackendUrl()
      : 'http://localhost:5000';
  },

  getAdminHeader() {
    return {
      'Content-Type': 'application/json',
      'X-Admin-Token': wx.getStorageSync('adminToken') || ''
    };
  },

  handleUnauthorized() {
    wx.removeStorageSync('adminToken');
    wx.removeStorageSync('adminUsername');
    wx.redirectTo({ url: '/pages/adminLogin/adminLogin' });
  },

  getTypeValue() {
    return ['', 'movie', 'series'][this.data.typeIndex] || '';
  },

  onKeywordInput(e) {
    this.setData({ keyword: e.detail.value });
  },

  onTypeChange(e) {
    this.setData({ typeIndex: Number(e.detail.value) }, () => {
      this.fetchContent(1);
    });
  },

  fetchContent(page = 1) {
    this.setData({ loading: true, error: '' });
    wx.request({
      url: `${this.getBackendUrl()}/api/admin/content`,
      data: {
        page,
        type: this.getTypeValue(),
        q: this.data.keyword
      },
      header: this.getAdminHeader(),
      success: (res) => {
        if (res.statusCode === 401) {
          this.handleUnauthorized();
          return;
        }

        if (res.data && res.data.code === 0) {
          const payload = res.data.data || {};
          this.setData({
            items: payload.items || [],
            page: payload.page || 1,
            pages: payload.pages || 1,
            total: payload.total || 0,
            loading: false
          });
          return;
        }

        this.setData({
          loading: false,
          error: (res.data && res.data.error) || '加载失败'
        });
      },
      fail: () => {
        this.setData({ loading: false, error: '网络错误，加载失败' });
      }
    });
  },

  search() {
    this.fetchContent(1);
  },

  prevPage() {
    if (this.data.page <= 1) {
      return;
    }
    this.fetchContent(this.data.page - 1);
  },

  nextPage() {
    if (this.data.page >= this.data.pages) {
      return;
    }
    this.fetchContent(this.data.page + 1);
  }
});
