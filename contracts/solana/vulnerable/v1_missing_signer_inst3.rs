use anchor_lang::prelude::*;

declare_id!("VAULT111111111111111111111111111111111111111");

#[program]
pub mod vault {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>, authority: Pubkey) -> Result<()> {
        let vault = &mut ctx.accounts.vault;
        vault.authority = authority;
        vault.locked = false;
        vault.bump = *ctx.bumps.get("vault").unwrap();
        Ok(())
    }

    pub fn unlock_vault(ctx: Context<UnlockVault>) -> Result<()> {
        let vault = &mut ctx.accounts.vault;
        require!(
            ctx.accounts.caller.key() == vault.authority,
            VaultError::Unauthorized
        );
        vault.locked = false;
        Ok(())
    }

    pub fn withdraw(ctx: Context<Withdraw>, amount: u64) -> Result<()> {
        require!(!ctx.accounts.vault.locked, VaultError::VaultLocked);
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + Vault::SIZE,
        seeds = [b"vault"],
        bump
    )]
    pub vault: Account<'info, Vault>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct UnlockVault<'info> {
    #[account(mut, seeds = [b"vault"], bump = vault.bump)]
    pub vault: Account<'info, Vault>,
    pub caller: AccountInfo<'info>,
}

#[derive(Accounts)]
pub struct Withdraw<'info> {
    #[account(seeds = [b"vault"], bump = vault.bump)]
    pub vault: Account<'info, Vault>,
    pub withdrawer: Signer<'info>,
}

#[account]
pub struct Vault {
    pub authority: Pubkey,
    pub locked: bool,
    pub bump: u8,
}

impl Vault {
    pub const SIZE: usize = 32 + 1 + 1;
}

#[error_code]
pub enum VaultError {
    #[msg("Caller is not the authority")]
    Unauthorized,
    #[msg("Vault is locked")]
    VaultLocked,
}
