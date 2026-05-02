Page({
  data: {
    theme: 'light',
    notifications: true,
    recommendMode: 'auto',
    recommendModeIndex: 0,
    recommendModeOptions: ['自动推荐', '手动筛选'],
    cacheSize: '0 MB'
  },

  onLoad() {
    this.loadSettings();
    this.calculateCacheSize();
  },

  saveSettings(extra = {}) {
    wx.setStorageSync('appSettings', {
      theme: this.data.theme,
      notifications: this.data.notifications,
      recommendMode: this.data.recommendMode,
      ...extra
    });
  },

  loadSettings() {
    const savedSettings = wx.getStorageSync('appSettings') || {};
    const recommendMode = savedSettings.recommendMode || 'auto';

    this.setData({
      theme: savedSettings.theme || 'light',
      notifications: savedSettings.notifications !== undefined ? savedSettings.notifications : true,
      recommendMode,
      recommendModeIndex: recommendMode === 'manual' ? 1 : 0
    });
  },

  toggleTheme(e) {
    const theme = e.detail.value ? 'dark' : 'light';
    this.setData({ theme });
    this.saveSettings({ theme });
    wx.showToast({
      title: `${theme === 'dark' ? '深色' : '浅色'}主题已启用`,
      icon: 'none'
    });
  },

  toggleNotifications(e) {
    const notifications = e.detail.value;
    this.setData({ notifications });
    this.saveSettings({ notifications });
  },

  changeRecommendMode(e) {
    const recommendModeIndex = Number(e.detail.value);
    const recommendMode = recommendModeIndex === 0 ? 'auto' : 'manual';
    this.setData({ recommendMode, recommendModeIndex });
    this.saveSettings({ recommendMode });
  },

  calculateCacheSize() {
    wx.getStorageInfo({
      success: (res) => {
        const size = (res.currentSize / 1024).toFixed(2);
        this.setData({ cacheSize: `${size} MB` });
      },
      fail: () => {
        this.setData({ cacheSize: '获取失败' });
      }
    });
  },

  clearCache() {
    wx.showModal({
      title: '确认清除',
      content: '确定要清除所有本地缓存吗？',
      success: (res) => {
        if (res.confirm) {
          wx.clearStorage({
            success: () => {
              this.setData({
                cacheSize: '0 MB',
                theme: 'light',
                notifications: true,
                recommendMode: 'auto',
                recommendModeIndex: 0
              });
              wx.showToast({ title: '缓存已清除', icon: 'success' });
            },
            fail: () => {
              wx.showToast({ title: '清除失败', icon: 'none' });
            }
          });
        }
      }
    });
  },

  goToAdmin() {
    wx.navigateTo({
      url: '/pages/adminLogin/adminLogin'
    });
  },

  goBack() {
    wx.navigateBack();
  }
});
