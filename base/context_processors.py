from store.utils import cookieCart, cartData, guestOrder


def default(request):
     # cart = request.COOKIES['cart']
     cart = request.COOKIES.get('cart', '{}')
     
     data = cartData(request)
     cartItems = data['cartItems']
     return { 'cartItems':cartItems}