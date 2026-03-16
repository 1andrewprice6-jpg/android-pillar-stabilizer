using UnityEngine;
using System.Collections.Generic;

namespace NeonProtocol.Maps.Radioactive
{
    [System.Serializable]
    public struct ChemicalRecipe
    {
        public string ingredientA;
        public string ingredientB;
        public GameObject resultPrefab;
    }

    public class RadioactiveManager : MonoBehaviour
    {
        [Header("Crafting Station")]
        [SerializeField] private List<ChemicalRecipe> recipes;
        
        private string _slotA;
        private string _slotB;

        public void AddIngredient(string ingredientName)
        {
            if (string.IsNullOrEmpty(_slotA))
                _slotA = ingredientName;
            else if (string.IsNullOrEmpty(_slotB))
            {
                _slotB = ingredientName;
                Mix();
            }
        }

        private void Mix() // Fixed function name case from 'Mix chemicals' to 'Mix'
        {
            foreach (var recipe in recipes)
            {
                if ((recipe.ingredientA == _slotA && recipe.ingredientB == _slotB) ||
                    (recipe.ingredientA == _slotB && recipe.ingredientB == _slotA))
                {
                    // Success
                    if (recipe.resultPrefab != null)
                        Instantiate(recipe.resultPrefab, transform.position + Vector3.up, Quaternion.identity);
                    else
                        Debug.Log($"Created {_slotA}+{_slotB} Item!");
                    
                    ClearSlots();
                    return;
                }
            }
            
            // Failure - Explosion?
            if (NeonProtocol.Core.Systems.NeonPooler.Instance != null)
            {
                NeonProtocol.Core.Systems.NeonPooler.Instance.Spawn("Explosion", transform.position, Quaternion.identity);
            }
            else
            {
                Debug.Log("Volatile Mixture! BOOM! (No Pooler)");
            }
            ClearSlots();
        }

        private void ClearSlots()
        {
            _slotA = "";
            _slotB = "";
        }
    }
}