// pages/mine/mine.js
Page({
  data: {
    userInfo: {
      avatarUrl: '/images/default_avatar.png', // 默认头像
      username: '未登录用户'
    }
  },

  onLoad() {
    // 可以在这里加载用户信息，例如：
    // const userInfo = wx.getStorageSync('userInfo') || this.data.userInfo;
    // this.setData({ userInfo });
  },

  // 导出用户偏好数据
  exportUserData() {
    try {
      const userMovies = wx.getStorageSync('totalMovieList') || [];
      
      if (userMovies.length === 0) {
        wx.showToast({ title: '暂无数据可导出', icon: 'none' });
        return;
      }
      
      const exportData = {
        userId: 'user_' + Date.now(), // 生成唯一ID
        exportTime: new Date().toISOString(),
        preferences: userMovies.map(movie => ({
          movieName: movie.name,
          userScore: movie.score,
          genres: movie.selectedElements,
          addTime: movie.createTime
        }))
      };
      
      const jsonStr = JSON.stringify(exportData, null, 2);
      
      wx.setClipboardData({
        data: jsonStr,
        success: () => {
          wx.showModal({
            title: '导出成功',
            content: '已复制偏好数据到剪贴板，请粘贴到Python环境中训练模型。',
            confirmText: '知道了'
          });
        },
        fail: () => {
          wx.showToast({ title: '剪贴板操作失败', icon: 'none' });
        }
      });
      
    } catch (error) {
      console.error('导出失败:', error);
      wx.showToast({ title: '导出异常，请重试', icon: 'none' });
    }
  },

  // 跳转到设置页面
  goToSetting() {
    wx.navigateTo({
      url: '/pages/setting/setting' // 需要先创建设置页面
    });
  }
});