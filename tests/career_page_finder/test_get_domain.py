"""
Tests for get_domain module - Integration tests with data-driven approach.
"""

import pytest
import os
from agent_zoo.career_page_finder.get_domain import find_company_url_sync


# Test data: (company_name, country, city, expected_url)
TEST_COMPANIES = [
    ("Cubert", "Germany", "Ulm", "https://cubert-hyperspectral.com/"),
    ("Asys", "Germany", "Dornstadt", "https://www.asys-group.com/"),
    ("Max-Planck Institute for intelligent systems", "Germany", "Tuebingen", "https://is.mpg.de/"),
    ("Transporeon", "Germany", "Ulm", "https://www.transporeon.com"),
]


@pytest.mark.integration
class TestCompanyURLFinder:
    """Integration tests for CompanyURLFinder with real API calls."""
    
    @pytest.mark.parametrize("company_name,country,city,expected_url", TEST_COMPANIES)
    def test_find_company_url(self, company_name, country, city, expected_url):
        """Test finding URL for each company in the test data."""
        # Skip if API keys are not available
        if not os.getenv("OPENAI_API_KEY") and not os.getenv("BRAVE_API_KEY") and not os.getenv("SERPER_API_KEY"):
            pytest.skip("No API keys available for testing")
        
        result = find_company_url_sync(company_name, city, country)
        
        # Basic assertions
        assert result.company_info.name == company_name
        assert result.company_info.city == city
        assert result.company_info.country == country
        
        # Should find some URL
        assert result.url is not None, f"No URL found for {company_name}"
        assert result.url.startswith("http"), f"Invalid URL format for {company_name}: {result.url}"
        assert result.confidence > 0, f"Zero confidence for {company_name}"
        
        # Validation should be boolean
        assert isinstance(result.validated, bool), f"Invalid validation type for {company_name}"
        
        # Should use validator_agent method
        assert result.method == "validator_agent", f"Unexpected method for {company_name}: {result.method}"
        
        # No errors
        assert result.error is None, f"Error occurred for {company_name}: {result.error}"
        
        # Check if URL matches expected (either exact match or domain match)
        expected_domain = expected_url.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
        actual_domain = result.url.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
        
        assert (result.url == expected_url or expected_domain in actual_domain.lower()), \
            f"URL mismatch for {company_name}. Expected: {expected_url}, Got: {result.url}"
    
    def test_comprehensive_report(self):
        """Run all companies and generate a comprehensive report."""
        # Skip if API keys are not available
        if not os.getenv("OPENAI_API_KEY") and not os.getenv("BRAVE_API_KEY") and not os.getenv("SERPER_API_KEY"):
            pytest.skip("No API keys available for testing")
        
        results = []
        successful_tests = 0
        total_tests = len(TEST_COMPANIES)
        
        print(f"\n{'='*80}")
        print(f"COMPREHENSIVE COMPANY URL FINDER TEST REPORT")
        print(f"{'='*80}")
        print(f"Testing {total_tests} companies...")
        print()
        
        for i, (company_name, country, city, expected_url) in enumerate(TEST_COMPANIES, 1):
            print(f"{i}. Testing: {company_name}, {city}, {country}")
            print(f"   Expected URL: {expected_url}")
            
            try:
                result = find_company_url_sync(company_name, city, country)
                
                # Check if result is successful
                success = (
                    result.url is not None and 
                    result.url.startswith("http") and 
                    result.confidence > 0 and 
                    result.error is None
                )
                
                if success:
                    successful_tests += 1
                    status = "✅ SUCCESS"
                else:
                    status = "❌ FAILED"
                
                # Check URL match
                expected_domain = expected_url.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
                actual_domain = result.url.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/") if result.url else ""
                url_match = expected_domain in actual_domain.lower() if actual_domain else False
                
                print(f"   Found URL: {result.url}")
                print(f"   Confidence: {result.confidence}")
                print(f"   Validated: {result.validated}")
                print(f"   Method: {result.method}")
                print(f"   URL Match: {'✅' if url_match else '❌'}")
                print(f"   Status: {status}")
                
                results.append({
                    'company': company_name,
                    'expected_url': expected_url,
                    'found_url': result.url,
                    'confidence': result.confidence,
                    'validated': result.validated,
                    'method': result.method,
                    'success': success,
                    'url_match': url_match,
                    'error': result.error
                })
                
            except Exception as e:
                print(f"   Status: ❌ EXCEPTION - {str(e)}")
                results.append({
                    'company': company_name,
                    'expected_url': expected_url,
                    'found_url': None,
                    'confidence': 0,
                    'validated': False,
                    'method': None,
                    'success': False,
                    'url_match': False,
                    'error': str(e)
                })
            
            print("-" * 80)
        
        # Final summary
        success_rate = (successful_tests / total_tests) * 100
        url_matches = sum(1 for r in results if r['url_match'])
        url_match_rate = (url_matches / total_tests) * 100
        
        print(f"\nFINAL SUMMARY:")
        print(f"Total Companies Tested: {total_tests}")
        print(f"Successful Lookups: {successful_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"URL Matches: {url_matches}")
        print(f"URL Match Rate: {url_match_rate:.1f}%")
        print(f"{'='*80}")
        
        # Assert that we have reasonable success
        assert successful_tests > 0, "No companies were successfully processed"
        assert success_rate >= 50, f"Success rate too low: {success_rate:.1f}%"
