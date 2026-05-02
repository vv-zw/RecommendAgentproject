Page({
  data: {
    url: ''
  },
  onLoad(options) {
    this.setData({ url: decodeURIComponent(options.url) });
  },
  onReady() {
    // 页面渲染完成
  },
  onShow() {
    // 页面显示
  },
  onHide() {
    // 页面隐藏
  },
  onUnload() {
    // 页面卸载
  },
  onRefresh() {
    // 刷新当前页面
    wx.navigateBack();
    setTimeout(() => {
      wx.navigateTo({ url: `/pages/movieRecommend/movieRecommend` });
    }, 500);
  }
});