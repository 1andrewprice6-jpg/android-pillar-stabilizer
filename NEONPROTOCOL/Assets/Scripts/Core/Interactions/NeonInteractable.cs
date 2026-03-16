using UnityEngine;
using NeonProtocol.Core.Economy;

namespace NeonProtocol.Core.Interactions
{
    public abstract class NeonInteractable : MonoBehaviour
    {
        [Header("Interaction Settings")]
        [SerializeField] protected string interactionPrompt;
        [SerializeField] protected int cost;

        public string GetPrompt() => $"{interactionPrompt} [${cost}]";

        public virtual void Interact()
        {
            if (PointsSystem.Instance.TrySpendPoints(cost))
            {
                OnPurchaseSuccess();
            }
            else
            {
                OnPurchaseFail();
            }
        }

        protected abstract void OnPurchaseSuccess();
        
        protected virtual void OnPurchaseFail()
        {
            Debug.Log("Not enough points!");
        }
    }
}