Page({
  data: {
    total: 0,      // 总记录数
    avgScore: 0    // 平均评分
  },

  onLoad() {
    const list = wx.getStorageSync('movieList') || [];
    const total = list.length;
    if (total === 0) {
      this.setData({ total: 0, avgScore: 0 });
      return;
    }

    // 计算平均分
    const sum = list.reduce((sum, item) => sum + item.score, 0);
    const avg = sum / total;
    this.setData({ total, avgScore: avg });
  }
});