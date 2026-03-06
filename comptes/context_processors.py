from django.db.models import Q

def notifications_context(request):
    """
    Context processor pour ajouter les compteurs de notifications dans tous les templates
    """
    context = {
        'pending_orders_count': 0,
        'packaged_orders_count': 0,
        'unread_messages_count': 0,
    }
    
    if request.user.is_authenticated:
       
        from chat.models import Message, Conversation
        
        
        # Compteur de messages non lus pour tous les utilisateurs
        # Messages non lus = messages où l'utilisateur n'est pas l'expéditeur et lu=False
        conversations = Conversation.objects.filter(
            Q(participant1=request.user) | Q(participant2=request.user)
        )
        context['unread_messages_count'] = Message.objects.filter(
            Q(conversation__in=conversations) & ~Q(sender=request.user),
            lu=False
        ).count()
    
    return context

